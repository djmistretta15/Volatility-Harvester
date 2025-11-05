"""
Base exchange adapter interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from app.core.models import MarketData, OrderRequest, OrderFill
from app.core.enums import OrderStatus
import asyncio


class ExchangeAdapter(ABC):
    """Base class for exchange adapters."""

    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.connected = False
        self.last_heartbeat: Optional[datetime] = None

    @abstractmethod
    async def connect(self):
        """Connect to exchange (WebSocket, etc.)."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect from exchange."""
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> MarketData:
        """Get current market data for symbol."""
        pass

    @abstractmethod
    async def get_balance(self, asset: str) -> Decimal:
        """Get balance for a specific asset."""
        pass

    @abstractmethod
    async def get_balances(self) -> Dict[str, Decimal]:
        """Get all balances."""
        pass

    @abstractmethod
    async def place_order(self, symbol: str, order: OrderRequest) -> str:
        """
        Place an order.
        Returns order ID.
        """
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order. Returns True if successful."""
        pass

    @abstractmethod
    async def get_order_status(self, symbol: str, order_id: str) -> OrderStatus:
        """Get order status."""
        pass

    @abstractmethod
    async def get_order_fills(self, symbol: str, order_id: str) -> List[OrderFill]:
        """Get fills for an order."""
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: str) -> List[Dict]:
        """Get open orders for symbol."""
        pass

    @abstractmethod
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades."""
        pass

    @abstractmethod
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get OHLCV candles.
        Returns list of dicts with keys: timestamp, open, high, low, close, volume
        """
        pass

    @abstractmethod
    def get_fees(self) -> Tuple[Decimal, Decimal]:
        """
        Get maker and taker fees.
        Returns (maker_fee, taker_fee) as decimals (e.g., 0.001 for 0.1%)
        """
        pass

    @abstractmethod
    def get_min_notional(self, symbol: str) -> Decimal:
        """Get minimum notional value for orders."""
        pass

    @abstractmethod
    def get_lot_size(self, symbol: str) -> Decimal:
        """Get lot size (minimum quantity increment)."""
        pass

    @abstractmethod
    def get_price_precision(self, symbol: str) -> int:
        """Get price precision (decimal places)."""
        pass

    async def health_check(self) -> bool:
        """
        Check if exchange connection is healthy.
        Returns True if healthy, False otherwise.
        """
        if not self.connected:
            return False

        if self.last_heartbeat is None:
            return False

        # Check if last heartbeat was within acceptable time
        time_since_heartbeat = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return time_since_heartbeat < 10  # 10 seconds threshold

    def round_price(self, symbol: str, price: Decimal) -> Decimal:
        """Round price to exchange precision."""
        precision = self.get_price_precision(symbol)
        return Decimal(str(round(float(price), precision)))

    def round_quantity(self, symbol: str, qty: Decimal) -> Decimal:
        """Round quantity to exchange lot size."""
        lot_size = self.get_lot_size(symbol)
        return (qty // lot_size) * lot_size
