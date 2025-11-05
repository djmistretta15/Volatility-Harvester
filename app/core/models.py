"""
Database models and dataclasses for the trading system.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from .enums import Side, OrderType, OrderStatus, PositionStatus, TradingMode, StrategyState

Base = declarative_base()


class Candle(Base):
    """OHLCV candle data."""
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    ts = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    source = Column(String(50), nullable=False)  # exchange or 'backtest'
    timeframe = Column(String(10), nullable=False)  # 1m, 5m, 15m, etc.

    __table_args__ = (
        {"schema": None}
    )


class Trade(Base):
    """Executed trade record."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, nullable=False, index=True)
    side = Column(SQLEnum(Side), nullable=False)
    qty = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, nullable=False)
    fee_asset = Column(String(10), nullable=False)
    pnl = Column(Float, nullable=True)  # Realized PnL for this trade
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=True, index=True)
    mode = Column(SQLEnum(TradingMode), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    run = relationship("Run", back_populates="trades")
    position = relationship("Position", back_populates="trades")


class Order(Base):
    """Order record."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, nullable=False, index=True)
    side = Column(SQLEnum(Side), nullable=False)
    order_type = Column(SQLEnum(OrderType), nullable=False)
    status = Column(SQLEnum(OrderStatus), nullable=False, index=True)
    qty = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # Null for market orders
    filled_qty = Column(Float, nullable=False, default=0.0)
    filled_price = Column(Float, nullable=True)
    exchange_id = Column(String(100), nullable=True)  # Exchange order ID
    reason = Column(String(200), nullable=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=True, index=True)
    mode = Column(SQLEnum(TradingMode), nullable=False)
    idempotency_key = Column(String(100), nullable=True, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    run = relationship("Run", back_populates="orders")


class Position(Base):
    """Position record (entry to exit)."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_open = Column(DateTime, nullable=False, index=True)
    ts_close = Column(DateTime, nullable=True)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    qty = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=True)
    realized_pnl_pct = Column(Float, nullable=True)
    status = Column(SQLEnum(PositionStatus), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=True, index=True)
    mode = Column(SQLEnum(TradingMode), nullable=False)
    fees_paid = Column(Float, nullable=False, default=0.0)
    notes = Column(Text, nullable=True)

    run = relationship("Run", back_populates="positions")
    trades = relationship("Trade", back_populates="position")


class Run(Base):
    """Trading run (backtest, paper, or live session)."""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mode = Column(SQLEnum(TradingMode), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    stopped_at = Column(DateTime, nullable=True)
    config_json = Column(JSON, nullable=False)
    notes = Column(Text, nullable=True)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=True)
    total_pnl = Column(Float, nullable=True)
    total_pnl_pct = Column(Float, nullable=True)
    max_drawdown_pct = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)

    trades = relationship("Trade", back_populates="run")
    orders = relationship("Order", back_populates="run")
    positions = relationship("Position", back_populates="run")


class State(Base):
    """Key-value store for strategy state."""
    __tablename__ = "state"

    key = Column(String(100), primary_key=True)
    value_json = Column(JSON, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# Dataclasses for in-memory state management

@dataclass
class StrategyStateData:
    """Strategy state data (persisted to DB)."""
    state: StrategyState = StrategyState.FLAT
    last_peak: Optional[Decimal] = None
    last_trough: Optional[Decimal] = None
    last_buy_price: Optional[Decimal] = None
    last_sell_price: Optional[Decimal] = None
    current_position_qty: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    total_equity: Decimal = Decimal("0")
    peak_equity: Decimal = Decimal("0")
    current_drawdown_pct: Decimal = Decimal("0")
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    atr_pct: Optional[Decimal] = None
    adaptive_buy_threshold: Optional[Decimal] = None
    adaptive_sell_threshold: Optional[Decimal] = None
    paused: bool = False
    pause_reason: Optional[str] = None
    last_update: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MarketData:
    """Current market data snapshot."""
    symbol: str
    timestamp: datetime
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume_24h: Optional[Decimal] = None

    @property
    def mid(self) -> Decimal:
        """Mid price."""
        return (self.bid + self.ask) / Decimal("2")

    @property
    def spread_bps(self) -> Decimal:
        """Spread in basis points."""
        if self.mid == 0:
            return Decimal("0")
        return ((self.ask - self.bid) / self.mid) * Decimal("10000")


@dataclass
class Signal:
    """Trading signal."""
    timestamp: datetime
    signal_type: str  # buy, sell, hold
    price: Decimal
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderRequest:
    """Order request."""
    side: Side
    order_type: OrderType
    qty: Decimal
    price: Optional[Decimal] = None
    post_only: bool = False
    timeout_seconds: int = 30
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderFill:
    """Order fill event."""
    order_id: str
    timestamp: datetime
    side: Side
    qty: Decimal
    price: Decimal
    fee: Decimal
    fee_asset: str
