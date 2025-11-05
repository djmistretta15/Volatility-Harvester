"""
Risk management module with circuit breakers.
"""
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.core.models import StrategyStateData, MarketData
from app.core.enums import StrategyState, CircuitBreakerReason
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Risk management with multiple circuit breakers.

    Circuit breakers:
    1. Max drawdown
    2. Consecutive losses
    3. Daily loss limit
    4. Volatility bounds (too low or too high)
    5. Spread guard
    6. Latency guard
    """

    def __init__(self):
        self.daily_pnl_reset_time: Optional[datetime] = None
        self.daily_pnl: Decimal = Decimal("0")

    def check_drawdown(self, state: StrategyStateData) -> Tuple[bool, Optional[str]]:
        """
        Check if drawdown exceeds maximum allowed.

        Returns:
            (should_pause, reason)
        """
        if state.peak_equity == 0:
            return (False, None)

        current_dd_pct = state.current_drawdown_pct

        if current_dd_pct >= settings.max_drawdown_pct:
            reason = f"Drawdown {current_dd_pct:.2f}% exceeds limit {settings.max_drawdown_pct:.2f}%"
            logger.warning(f"Circuit breaker: {reason}")
            return (True, reason)

        return (False, None)

    def check_consecutive_losses(self, state: StrategyStateData) -> Tuple[bool, Optional[str]]:
        """
        Check if consecutive losses exceed maximum.

        Returns:
            (should_pause, reason)
        """
        if state.consecutive_losses >= settings.max_consecutive_losses:
            reason = f"Consecutive losses {state.consecutive_losses} exceeds limit {settings.max_consecutive_losses}"
            logger.warning(f"Circuit breaker: {reason}")
            return (True, reason)

        return (False, None)

    def check_daily_loss_limit(self, state: StrategyStateData) -> Tuple[bool, Optional[str]]:
        """
        Check if daily loss exceeds limit.

        Returns:
            (should_pause, reason)
        """
        now = datetime.utcnow()

        # Reset daily PnL at midnight UTC
        if self.daily_pnl_reset_time is None or now.date() > self.daily_pnl_reset_time.date():
            self.daily_pnl = Decimal("0")
            self.daily_pnl_reset_time = now
            logger.debug("Reset daily PnL counter")

        # Calculate daily loss percentage
        if state.total_equity == 0:
            return (False, None)

        daily_loss_pct = abs(self.daily_pnl / state.total_equity * Decimal("100"))

        if self.daily_pnl < 0 and daily_loss_pct >= settings.daily_loss_limit_pct:
            reason = f"Daily loss {daily_loss_pct:.2f}% exceeds limit {settings.daily_loss_limit_pct:.2f}%"
            logger.warning(f"Circuit breaker: {reason}")
            return (True, reason)

        return (False, None)

    def update_daily_pnl(self, pnl: Decimal):
        """Update daily PnL tracker."""
        self.daily_pnl += pnl
        logger.debug(f"Daily PnL: ${self.daily_pnl:.2f}")

    def check_volatility_bounds(self, atr_pct: Optional[Decimal]) -> Tuple[bool, Optional[str]]:
        """
        Check if volatility is within acceptable bounds.

        Returns:
            (should_pause, reason)
        """
        if atr_pct is None:
            return (False, None)

        if atr_pct < settings.min_activity_pct:
            reason = f"ATR {atr_pct:.2f}% below minimum {settings.min_activity_pct:.2f}% (too choppy)"
            logger.warning(f"Circuit breaker: {reason}")
            return (True, reason)

        if atr_pct > settings.max_activity_pct:
            reason = f"ATR {atr_pct:.2f}% above maximum {settings.max_activity_pct:.2f}% (too volatile)"
            logger.warning(f"Circuit breaker: {reason}")
            return (True, reason)

        return (False, None)

    def check_spread(self, market_data: MarketData) -> Tuple[bool, Optional[str]]:
        """
        Check if spread is within acceptable bounds.

        Returns:
            (should_pause, reason)
        """
        spread_bps = market_data.spread_bps

        if spread_bps > settings.max_spread_bps:
            reason = f"Spread {spread_bps:.1f} bps exceeds limit {settings.max_spread_bps} bps"
            logger.warning(f"Circuit breaker: {reason}")
            return (True, reason)

        return (False, None)

    def check_stale_data(self, last_heartbeat: Optional[datetime]) -> Tuple[bool, Optional[str]]:
        """
        Check if data is stale (WebSocket lag).

        Returns:
            (should_pause, reason)
        """
        if last_heartbeat is None:
            return (True, "No heartbeat received")

        time_since_heartbeat = (datetime.utcnow() - last_heartbeat).total_seconds()

        if time_since_heartbeat > settings.max_ws_stale_seconds:
            reason = f"Data stale for {time_since_heartbeat:.1f}s (limit {settings.max_ws_stale_seconds}s)"
            logger.warning(f"Circuit breaker: {reason}")
            return (True, reason)

        return (False, None)

    def check_all_circuit_breakers(
        self,
        state: StrategyStateData,
        market_data: MarketData,
        last_heartbeat: Optional[datetime]
    ) -> Tuple[bool, Optional[CircuitBreakerReason], Optional[str]]:
        """
        Check all circuit breakers.

        Returns:
            (should_pause, reason_enum, reason_text)
        """
        # Check drawdown
        should_pause, reason = self.check_drawdown(state)
        if should_pause:
            return (True, CircuitBreakerReason.MAX_DRAWDOWN, reason)

        # Check consecutive losses
        should_pause, reason = self.check_consecutive_losses(state)
        if should_pause:
            return (True, CircuitBreakerReason.CONSECUTIVE_LOSSES, reason)

        # Check daily loss limit
        should_pause, reason = self.check_daily_loss_limit(state)
        if should_pause:
            return (True, CircuitBreakerReason.DAILY_LOSS_LIMIT, reason)

        # Check volatility bounds
        should_pause, reason = self.check_volatility_bounds(state.atr_pct)
        if should_pause:
            if "too choppy" in reason.lower():
                return (True, CircuitBreakerReason.LOW_VOLATILITY, reason)
            else:
                return (True, CircuitBreakerReason.HIGH_VOLATILITY, reason)

        # Check spread
        should_pause, reason = self.check_spread(market_data)
        if should_pause:
            return (True, CircuitBreakerReason.SPREAD_TOO_WIDE, reason)

        # Check stale data
        should_pause, reason = self.check_stale_data(last_heartbeat)
        if should_pause:
            return (True, CircuitBreakerReason.STALE_DATA, reason)

        return (False, None, None)

    def update_drawdown(self, state: StrategyStateData):
        """Update drawdown calculation."""
        if state.total_equity > state.peak_equity:
            state.peak_equity = state.total_equity
            state.current_drawdown_pct = Decimal("0")
        elif state.peak_equity > 0:
            dd = (state.peak_equity - state.total_equity) / state.peak_equity * Decimal("100")
            state.current_drawdown_pct = dd

    def validate_order_size(
        self,
        qty: Decimal,
        price: Decimal,
        min_notional: Decimal,
        lot_size: Decimal
    ) -> Tuple[bool, Optional[str], Decimal]:
        """
        Validate and adjust order size.

        Returns:
            (is_valid, error_reason, adjusted_qty)
        """
        # Check minimum notional
        notional = qty * price
        if notional < min_notional:
            return (False, f"Notional ${notional:.2f} below minimum ${min_notional:.2f}", Decimal("0"))

        # Round to lot size
        adjusted_qty = (qty // lot_size) * lot_size

        if adjusted_qty <= 0:
            return (False, "Quantity too small after rounding to lot size", Decimal("0"))

        return (True, None, adjusted_qty)

    def should_flatten_position(
        self,
        state: StrategyStateData,
        market_data: MarketData,
        last_heartbeat: Optional[datetime]
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if position should be flattened immediately (emergency exit).

        Returns:
            (should_flatten, reason)
        """
        # Only flatten on critical circuit breakers
        should_pause, cb_reason, reason_text = self.check_all_circuit_breakers(
            state, market_data, last_heartbeat
        )

        if should_pause:
            # Flatten on max drawdown or stale data
            if cb_reason in [CircuitBreakerReason.MAX_DRAWDOWN, CircuitBreakerReason.STALE_DATA]:
                return (True, reason_text)

        return (False, None)
