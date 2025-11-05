"""
Volatility Harvesting Strategy Engine.

Core strategy: Buy on dips, sell on rebounds to harvest volatility.
"""
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Tuple
import pandas as pd
import numpy as np
from app.core.models import StrategyStateData, MarketData, Signal
from app.core.enums import StrategyState, SignalType
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class VolatilityHarvester:
    """
    Volatility harvesting strategy implementation.

    Strategy:
    - Buy when price drops X% from last peak (or last sell)
    - Sell when price rises Y% from last buy
    - Adaptive thresholds based on ATR
    - Single position (all-in/all-out) for full compounding
    """

    def __init__(
        self,
        buy_threshold_pct: Optional[Decimal] = None,
        sell_threshold_pct: Optional[Decimal] = None,
        adaptive: bool = True,
        min_swing_pct: Optional[Decimal] = None,
        max_swing_pct: Optional[Decimal] = None
    ):
        self.buy_threshold_pct = buy_threshold_pct or settings.buy_threshold_pct
        self.sell_threshold_pct = sell_threshold_pct or settings.sell_threshold_pct
        self.adaptive = adaptive
        self.min_swing_pct = min_swing_pct or settings.min_swing_pct
        self.max_swing_pct = max_swing_pct or settings.max_swing_pct

    def calculate_atr_pct(self, candles: pd.DataFrame, period: int = 14) -> Decimal:
        """
        Calculate ATR as percentage of price.

        Args:
            candles: DataFrame with columns [high, low, close]
            period: ATR period

        Returns:
            ATR as percentage of current price
        """
        if len(candles) < period + 1:
            return Decimal("0")

        # Calculate True Range
        high_low = candles['high'] - candles['low']
        high_close = np.abs(candles['high'] - candles['close'].shift())
        low_close = np.abs(candles['low'] - candles['close'].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)

        # Calculate ATR
        atr = true_range.rolling(window=period).mean().iloc[-1]
        current_price = candles['close'].iloc[-1]

        if current_price == 0:
            return Decimal("0")

        atr_pct = (atr / current_price) * 100
        return Decimal(str(atr_pct))

    def adapt_thresholds(self, atr_pct: Decimal) -> Tuple[Decimal, Decimal]:
        """
        Adapt buy/sell thresholds based on current volatility (ATR).

        Logic:
        - If ATR is low (< 2.5%), reduce thresholds to stay active
        - If ATR is high (> 6%), increase thresholds to avoid whipsaws
        - Scale linearly between min and max swing

        Args:
            atr_pct: Current ATR as percentage

        Returns:
            (buy_threshold, sell_threshold)
        """
        if not self.adaptive:
            return (self.buy_threshold_pct, self.sell_threshold_pct)

        # Map ATR to threshold range
        # ATR 2% -> min_swing
        # ATR 6% -> max_swing
        atr_min = Decimal("2.0")
        atr_max = Decimal("6.0")

        if atr_pct <= atr_min:
            adapted_threshold = self.min_swing_pct
        elif atr_pct >= atr_max:
            adapted_threshold = self.max_swing_pct
        else:
            # Linear interpolation
            ratio = (atr_pct - atr_min) / (atr_max - atr_min)
            adapted_threshold = self.min_swing_pct + ratio * (self.max_swing_pct - self.min_swing_pct)

        # Keep buy and sell thresholds proportional
        buy_threshold = adapted_threshold
        sell_threshold = adapted_threshold

        logger.debug(f"ATR: {atr_pct:.2f}% -> Thresholds: Buy={buy_threshold:.2f}%, Sell={sell_threshold:.2f}%")

        return (buy_threshold, sell_threshold)

    def check_trend_filter(self, candles: pd.DataFrame) -> bool:
        """
        Check trend filter (MA crossover).

        Returns True if trend is favorable (long MA above short MA),
        or if trend filter is disabled.
        """
        if not settings.use_trend_filter:
            return True

        if len(candles) < settings.ma_long:
            return True  # Not enough data, allow trading

        ma_short = candles['close'].rolling(window=settings.ma_short).mean().iloc[-1]
        ma_long = candles['close'].rolling(window=settings.ma_long).mean().iloc[-1]

        return ma_short > ma_long

    def generate_signal(
        self,
        state: StrategyStateData,
        market_data: MarketData,
        candles: Optional[pd.DataFrame] = None
    ) -> Signal:
        """
        Generate trading signal based on current state and market data.

        Args:
            state: Current strategy state
            market_data: Current market data
            candles: Recent candles for ATR calculation (optional)

        Returns:
            Signal object
        """
        current_price = market_data.mid
        timestamp = market_data.timestamp

        # Calculate ATR if candles provided
        atr_pct = None
        if candles is not None and len(candles) >= 15:
            atr_pct = self.calculate_atr_pct(candles)
            state.atr_pct = atr_pct

            # Adapt thresholds
            buy_threshold, sell_threshold = self.adapt_thresholds(atr_pct)
            state.adaptive_buy_threshold = buy_threshold
            state.adaptive_sell_threshold = sell_threshold
        else:
            buy_threshold = self.buy_threshold_pct
            sell_threshold = self.sell_threshold_pct

        # Check if paused
        if state.paused:
            return Signal(
                timestamp=timestamp,
                signal_type=SignalType.HOLD.value,
                price=current_price,
                reason=f"Paused: {state.pause_reason}"
            )

        # Check trend filter
        if candles is not None and not self.check_trend_filter(candles):
            return Signal(
                timestamp=timestamp,
                signal_type=SignalType.HOLD.value,
                price=current_price,
                reason="Trend filter: bearish trend"
            )

        # State machine logic
        if state.state == StrategyState.FLAT:
            # Looking for buy opportunity (dip)
            # Track peak price
            if state.last_peak is None or current_price > state.last_peak:
                state.last_peak = current_price
                logger.debug(f"New peak: {state.last_peak}")

            # Check if price dropped enough from peak
            drop_pct = ((state.last_peak - current_price) / state.last_peak) * Decimal("100")

            if drop_pct >= buy_threshold:
                return Signal(
                    timestamp=timestamp,
                    signal_type=SignalType.BUY.value,
                    price=current_price,
                    reason=f"Price dropped {drop_pct:.2f}% from peak ${state.last_peak:.2f}",
                    metadata={
                        "drop_pct": float(drop_pct),
                        "peak_price": float(state.last_peak),
                        "buy_threshold": float(buy_threshold),
                        "atr_pct": float(atr_pct) if atr_pct else None
                    }
                )

        elif state.state == StrategyState.LONG:
            # Looking for sell opportunity (rebound)
            # Track trough price
            if state.last_trough is None or current_price < state.last_trough:
                state.last_trough = current_price
                logger.debug(f"New trough: {state.last_trough}")

            # Check if price rose enough from entry
            if state.last_buy_price is None:
                logger.warning("In LONG state but no last_buy_price")
                return Signal(
                    timestamp=timestamp,
                    signal_type=SignalType.HOLD.value,
                    price=current_price,
                    reason="Missing buy price"
                )

            rise_pct = ((current_price - state.last_buy_price) / state.last_buy_price) * Decimal("100")

            if rise_pct >= sell_threshold:
                return Signal(
                    timestamp=timestamp,
                    signal_type=SignalType.SELL.value,
                    price=current_price,
                    reason=f"Price rose {rise_pct:.2f}% from entry ${state.last_buy_price:.2f}",
                    metadata={
                        "rise_pct": float(rise_pct),
                        "entry_price": float(state.last_buy_price),
                        "sell_threshold": float(sell_threshold),
                        "atr_pct": float(atr_pct) if atr_pct else None
                    }
                )

        # Default: hold
        return Signal(
            timestamp=timestamp,
            signal_type=SignalType.HOLD.value,
            price=current_price,
            reason="No trigger met"
        )

    def update_state_after_buy(
        self,
        state: StrategyStateData,
        fill_price: Decimal,
        qty: Decimal,
        timestamp: datetime
    ):
        """Update state after buy execution."""
        state.state = StrategyState.LONG
        state.last_buy_price = fill_price
        state.current_position_qty = qty
        state.last_trough = fill_price  # Reset trough to entry price
        state.last_update = timestamp
        logger.info(f"Entered LONG position at ${fill_price} qty={qty}")

    def update_state_after_sell(
        self,
        state: StrategyStateData,
        fill_price: Decimal,
        realized_pnl: Decimal,
        timestamp: datetime
    ):
        """Update state after sell execution."""
        state.state = StrategyState.FLAT
        state.last_sell_price = fill_price
        state.current_position_qty = Decimal("0")
        state.realized_pnl += realized_pnl
        state.last_peak = fill_price  # Reset peak to exit price
        state.last_update = timestamp

        # Track win/loss streak
        if realized_pnl > 0:
            state.consecutive_wins += 1
            state.consecutive_losses = 0
            state.winning_trades += 1
        else:
            state.consecutive_losses += 1
            state.consecutive_wins = 0

        state.total_trades += 1

        logger.info(f"Exited position at ${fill_price}, PnL=${realized_pnl:.2f}")

    def calculate_position_size(
        self,
        available_capital: Decimal,
        current_price: Decimal,
        reserve_pct: Optional[Decimal] = None
    ) -> Decimal:
        """
        Calculate position size for buy signal.

        Uses available capital minus reserve.

        Args:
            available_capital: Available cash
            current_price: Current market price
            reserve_pct: Reserve percentage to keep

        Returns:
            Quantity to buy
        """
        reserve = reserve_pct or settings.reserve_pct
        deployable_capital = available_capital * (Decimal("100") - reserve) / Decimal("100")

        if deployable_capital <= 0:
            return Decimal("0")

        qty = deployable_capital / current_price
        return qty
