"""
Enumerations for the trading system.
"""
from enum import Enum


class Side(str, Enum):
    """Order/trade side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    POST_ONLY = "post_only"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionStatus(str, Enum):
    """Position status."""
    OPEN = "open"
    CLOSED = "closed"


class TradingMode(str, Enum):
    """Trading mode."""
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class StrategyState(str, Enum):
    """Strategy state machine states."""
    FLAT = "flat"  # No position
    LONG = "long"  # Long position
    PAUSED = "paused"  # Circuit breaker triggered


class CircuitBreakerReason(str, Enum):
    """Reasons for circuit breaker activation."""
    MAX_DRAWDOWN = "max_drawdown"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    LOW_VOLATILITY = "low_volatility"
    HIGH_VOLATILITY = "high_volatility"
    SPREAD_TOO_WIDE = "spread_too_wide"
    STALE_DATA = "stale_data"
    MANUAL = "manual"


class SignalType(str, Enum):
    """Trading signal types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
