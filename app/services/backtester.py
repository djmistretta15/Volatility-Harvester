"""
Vectorized backtesting engine.

Simulates the volatility harvesting strategy on historical data.
"""
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from app.core.strategy import VolatilityHarvester
from app.core.risk import RiskManager
from app.core.portfolio import Portfolio
from app.core.models import StrategyStateData, MarketData, Signal
from app.core.enums import StrategyState, Side
from app.core.fees import calculate_trading_fee
from app.core.slippage import adjust_fill_price_for_slippage
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtest configuration."""
    initial_capital: Decimal = Decimal("10000")
    buy_threshold_pct: Decimal = Decimal("5.0")
    sell_threshold_pct: Decimal = Decimal("5.0")
    adaptive_thresholds: bool = True
    min_swing_pct: Decimal = Decimal("2.0")
    max_swing_pct: Decimal = Decimal("8.0")
    maker_fee_pct: Decimal = Decimal("0.10")
    taker_fee_pct: Decimal = Decimal("0.30")
    maker_first: bool = True
    maker_fill_rate: float = 0.7  # 70% of orders fill as maker
    reserve_pct: Decimal = Decimal("8.0")


@dataclass
class BacktestResult:
    """Backtest results."""
    initial_capital: float
    final_capital: float
    total_pnl: float
    total_pnl_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    cagr: float
    total_fees_paid: float
    total_slippage: float
    exposure_pct: float
    trades: List[Dict]
    equity_curve: pd.DataFrame
    config: Dict


class Backtester:
    """
    Vectorized backtester for volatility harvesting strategy.
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.strategy = VolatilityHarvester(
            buy_threshold_pct=self.config.buy_threshold_pct,
            sell_threshold_pct=self.config.sell_threshold_pct,
            adaptive=self.config.adaptive_thresholds,
            min_swing_pct=self.config.min_swing_pct,
            max_swing_pct=self.config.max_swing_pct
        )
        self.risk_manager = RiskManager()

    def run(
        self,
        candles: pd.DataFrame,
        symbol: str = "BTC-USD"
    ) -> BacktestResult:
        """
        Run backtest on historical candle data.

        Args:
            candles: DataFrame with columns [timestamp, open, high, low, close, volume]
            symbol: Trading symbol

        Returns:
            BacktestResult
        """
        logger.info(f"Starting backtest: {len(candles)} candles, initial capital ${self.config.initial_capital}")

        # Initialize state
        state = StrategyStateData()
        state.state = StrategyState.FLAT
        state.total_equity = self.config.initial_capital
        state.peak_equity = self.config.initial_capital

        portfolio = Portfolio(self.config.initial_capital)

        # Track results
        trades: List[Dict] = []
        equity_history: List[Tuple[datetime, float]] = []
        daily_returns: List[float] = []

        # Ensure candles are sorted
        if 'timestamp' not in candles.columns:
            candles = candles.reset_index()

        candles = candles.sort_values('timestamp')

        # Rolling window for ATR calculation
        atr_window = 30  # Need enough bars for ATR

        # Iterate through candles
        for i in range(atr_window, len(candles)):
            current_row = candles.iloc[i]
            timestamp = current_row['timestamp']
            price = Decimal(str(current_row['close']))

            # Get recent candles for ATR
            recent_candles = candles.iloc[max(0, i - atr_window):i + 1].copy()

            # Create market data
            spread = price * Decimal("0.0005")  # 5 bps spread
            market_data = MarketData(
                symbol=symbol,
                timestamp=timestamp,
                bid=price - spread / 2,
                ask=price + spread / 2,
                last=price
            )

            # Calculate ATR
            atr_pct = self.strategy.calculate_atr_pct(recent_candles)
            state.atr_pct = atr_pct

            # Check circuit breakers (simplified for backtest)
            should_pause, cb_reason, reason = self.risk_manager.check_all_circuit_breakers(
                state, market_data, timestamp
            )

            if should_pause and not state.paused:
                state.paused = True
                state.pause_reason = reason
                logger.warning(f"[{timestamp}] Circuit breaker: {reason}")

            # Generate signal
            signal = self.strategy.generate_signal(state, market_data, recent_candles)

            # Execute signal
            if signal.signal_type == "buy" and state.state == StrategyState.FLAT:
                # Calculate position size
                available_cash = portfolio.cash
                qty = self.strategy.calculate_position_size(
                    available_cash, price, self.config.reserve_pct
                )

                if qty > 0:
                    # Determine if maker or taker
                    is_maker = np.random.random() < self.config.maker_fill_rate if self.config.maker_first else False

                    # Adjust for slippage
                    fill_price = adjust_fill_price_for_slippage(price, "buy", atr_pct, is_maker)

                    # Calculate fee
                    notional = qty * fill_price
                    fee = calculate_trading_fee(notional, is_maker)

                    # Execute
                    try:
                        portfolio.execute_buy(qty, fill_price, fee)

                        # Update state
                        self.strategy.update_state_after_buy(state, fill_price, qty, timestamp)

                        # Record trade
                        trades.append({
                            "timestamp": timestamp,
                            "side": "buy",
                            "qty": float(qty),
                            "price": float(fill_price),
                            "fee": float(fee),
                            "is_maker": is_maker,
                            "reason": signal.reason
                        })

                        logger.info(f"[{timestamp}] BUY: {qty:.8f} @ ${fill_price:.2f}, fee=${fee:.2f}")

                    except ValueError as e:
                        logger.warning(f"[{timestamp}] Buy failed: {e}")

            elif signal.signal_type == "sell" and state.state == StrategyState.LONG:
                # Sell entire position
                qty = portfolio.btc

                if qty > 0:
                    # Determine if maker or taker
                    is_maker = np.random.random() < self.config.maker_fill_rate if self.config.maker_first else False

                    # Adjust for slippage
                    fill_price = adjust_fill_price_for_slippage(price, "sell", atr_pct, is_maker)

                    # Calculate fee
                    notional = qty * fill_price
                    fee = calculate_trading_fee(notional, is_maker)

                    # Calculate realized PnL
                    entry_cost = state.last_buy_price * qty
                    exit_revenue = fill_price * qty - fee
                    realized_pnl = exit_revenue - float(entry_cost)

                    # Execute
                    try:
                        portfolio.execute_sell(qty, fill_price, fee)

                        # Update state
                        self.strategy.update_state_after_sell(state, fill_price, Decimal(str(realized_pnl)), timestamp)

                        # Track daily PnL for risk management
                        self.risk_manager.update_daily_pnl(Decimal(str(realized_pnl)))

                        # Record trade
                        trades.append({
                            "timestamp": timestamp,
                            "side": "sell",
                            "qty": float(qty),
                            "price": float(fill_price),
                            "fee": float(fee),
                            "is_maker": is_maker,
                            "pnl": realized_pnl,
                            "reason": signal.reason
                        })

                        logger.info(f"[{timestamp}] SELL: {qty:.8f} @ ${fill_price:.2f}, PnL=${realized_pnl:.2f}")

                    except ValueError as e:
                        logger.warning(f"[{timestamp}] Sell failed: {e}")

            # Update portfolio state
            portfolio.sync_state(state, price)
            self.risk_manager.update_drawdown(state)

            # Record equity
            equity_history.append((timestamp, float(state.total_equity)))

            # Calculate daily return (simplified)
            if len(equity_history) > 1:
                prev_equity = equity_history[-2][1]
                if prev_equity > 0:
                    daily_return = (float(state.total_equity) - prev_equity) / prev_equity
                    daily_returns.append(daily_return)

        # Compile results
        result = self._compile_results(
            portfolio, state, trades, equity_history, daily_returns, candles
        )

        logger.info(f"Backtest complete: Final capital=${result.final_capital:.2f}, PnL=${result.total_pnl:.2f} ({result.total_pnl_pct:.2f}%)")
        logger.info(f"Trades: {result.total_trades}, Win rate: {result.win_rate:.2f}%, Max DD: {result.max_drawdown_pct:.2f}%")

        return result

    def _compile_results(
        self,
        portfolio: Portfolio,
        state: StrategyStateData,
        trades: List[Dict],
        equity_history: List[Tuple[datetime, float]],
        daily_returns: List[float],
        candles: pd.DataFrame
    ) -> BacktestResult:
        """Compile backtest results."""

        # Get final price for valuation
        final_price = Decimal(str(candles.iloc[-1]['close']))
        final_equity = portfolio.get_equity(final_price)

        # Calculate trade statistics
        total_trades = len([t for t in trades if t['side'] == 'sell'])
        winning_trades = len([t for t in trades if t['side'] == 'sell' and t.get('pnl', 0) > 0])
        losing_trades = len([t for t in trades if t['side'] == 'sell' and t.get('pnl', 0) < 0])

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        wins = [t['pnl'] for t in trades if t['side'] == 'sell' and t.get('pnl', 0) > 0]
        losses = [t['pnl'] for t in trades if t['side'] == 'sell' and t.get('pnl', 0) < 0]

        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0

        # Calculate fees and slippage
        total_fees = sum([t['fee'] for t in trades])
        # Slippage is implicit in fill prices

        # Calculate CAGR
        days = (candles.iloc[-1]['timestamp'] - candles.iloc[0]['timestamp']).days
        years = days / 365.25
        cagr = ((float(final_equity) / float(self.config.initial_capital)) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Calculate Sharpe ratio
        if len(daily_returns) > 0:
            sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
        else:
            sharpe = 0

        # Calculate Sortino ratio
        downside_returns = [r for r in daily_returns if r < 0]
        if len(downside_returns) > 0:
            sortino = np.mean(daily_returns) / np.std(downside_returns) * np.sqrt(252) if np.std(downside_returns) > 0 else 0
        else:
            sortino = 0

        # Calculate exposure
        in_market_bars = sum([1 for t in trades if t['side'] == 'buy']) * 2  # Rough estimate
        exposure_pct = (in_market_bars / len(candles)) * 100

        # Create equity curve DataFrame
        equity_df = pd.DataFrame(equity_history, columns=['timestamp', 'equity'])
        equity_df.set_index('timestamp', inplace=True)

        return BacktestResult(
            initial_capital=float(self.config.initial_capital),
            final_capital=float(final_equity),
            total_pnl=float(final_equity - self.config.initial_capital),
            total_pnl_pct=((float(final_equity) / float(self.config.initial_capital)) - 1) * 100,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_drawdown_pct=float(state.current_drawdown_pct),
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            cagr=cagr,
            total_fees_paid=total_fees,
            total_slippage=0,  # Included in prices
            exposure_pct=exposure_pct,
            trades=trades,
            equity_curve=equity_df,
            config=asdict(self.config)
        )

    def run_parameter_sweep(
        self,
        candles: pd.DataFrame,
        buy_thresholds: List[Decimal],
        sell_thresholds: List[Decimal]
    ) -> pd.DataFrame:
        """
        Run parameter sweep across threshold ranges.

        Args:
            candles: Historical candles
            buy_thresholds: List of buy thresholds to test
            sell_thresholds: List of sell thresholds to test

        Returns:
            DataFrame with results for each parameter combination
        """
        results = []

        total_combos = len(buy_thresholds) * len(sell_thresholds)
        logger.info(f"Running parameter sweep: {total_combos} combinations")

        for buy_thresh in buy_thresholds:
            for sell_thresh in sell_thresholds:
                logger.info(f"Testing: buy={buy_thresh}%, sell={sell_thresh}%")

                config = BacktestConfig(
                    buy_threshold_pct=buy_thresh,
                    sell_threshold_pct=sell_thresh,
                    adaptive_thresholds=False  # Use fixed for sweep
                )

                backtester = Backtester(config)
                result = backtester.run(candles)

                results.append({
                    "buy_threshold": float(buy_thresh),
                    "sell_threshold": float(sell_thresh),
                    "final_capital": result.final_capital,
                    "total_pnl_pct": result.total_pnl_pct,
                    "sharpe_ratio": result.sharpe_ratio,
                    "max_drawdown_pct": result.max_drawdown_pct,
                    "total_trades": result.total_trades,
                    "win_rate": result.win_rate
                })

        df = pd.DataFrame(results)
        logger.info("Parameter sweep complete")

        return df
