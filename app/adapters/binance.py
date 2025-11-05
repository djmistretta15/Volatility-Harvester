"""
Binance Spot API adapter.
"""
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import hmac
import hashlib
import time
import aiohttp
from urllib.parse import urlencode
from app.adapters.exchange_base import ExchangeAdapter
from app.core.models import MarketData, OrderRequest, OrderFill
from app.core.enums import OrderStatus, Side, OrderType
import logging

logger = logging.getLogger(__name__)


class BinanceAdapter(ExchangeAdapter):
    """Binance Spot API adapter."""

    BASE_URL = "https://api.binance.com"

    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)
        self.session: Optional[aiohttp.ClientSession] = None

    def _generate_signature(self, params: Dict) -> str:
        """Generate request signature."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def connect(self):
        """Connect."""
        self.session = aiohttp.ClientSession()
        self.connected = True
        self.last_heartbeat = datetime.utcnow()
        logger.info("Connected to Binance")

    async def disconnect(self):
        """Disconnect."""
        if self.session:
            await self.session.close()
        self.connected = False
        logger.info("Disconnected from Binance")

    async def _request(self, method: str, endpoint: str, signed: bool = False, params: Optional[Dict] = None) -> Dict:
        """Make request."""
        if not self.session:
            raise RuntimeError("Not connected")

        url = f"{self.BASE_URL}{endpoint}"
        headers = {"X-MBX-APIKEY": self.api_key}

        if params is None:
            params = {}

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._generate_signature(params)

        async with self.session.request(method, url, headers=headers, params=params) as response:
            self.last_heartbeat = datetime.utcnow()
            response.raise_for_status()
            return await response.json()

    async def get_ticker(self, symbol: str) -> MarketData:
        """Get ticker."""
        # Convert symbol: BTC-USD -> BTCUSDT for Binance
        binance_symbol = symbol.replace("-", "")
        if "USD" in binance_symbol and not "USDT" in binance_symbol:
            binance_symbol = binance_symbol.replace("USD", "USDT")

        data = await self._request("GET", "/api/v3/ticker/bookTicker", params={"symbol": binance_symbol})

        return MarketData(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            bid=Decimal(data["bidPrice"]),
            ask=Decimal(data["askPrice"]),
            last=Decimal(data["bidPrice"])  # Use bid as approximation
        )

    async def get_balance(self, asset: str) -> Decimal:
        """Get balance."""
        data = await self._request("GET", "/api/v3/account", signed=True)

        for balance in data["balances"]:
            if balance["asset"] == asset:
                return Decimal(balance["free"])

        return Decimal("0")

    async def get_balances(self) -> Dict[str, Decimal]:
        """Get all balances."""
        data = await self._request("GET", "/api/v3/account", signed=True)

        balances = {}
        for balance in data["balances"]:
            free = Decimal(balance["free"])
            if free > 0:
                balances[balance["asset"]] = free

        return balances

    async def place_order(self, symbol: str, order: OrderRequest) -> str:
        """Place order."""
        binance_symbol = symbol.replace("-", "")
        if "USD" in binance_symbol and not "USDT" in binance_symbol:
            binance_symbol = binance_symbol.replace("USD", "USDT")

        params = {
            "symbol": binance_symbol,
            "side": order.side.value.upper(),
            "quantity": str(float(order.qty))
        }

        if order.order_type == OrderType.MARKET:
            params["type"] = "MARKET"
        elif order.order_type == OrderType.LIMIT:
            params["type"] = "LIMIT"
            params["price"] = str(float(order.price))
            params["timeInForce"] = "GTC"
        elif order.order_type == OrderType.POST_ONLY:
            params["type"] = "LIMIT_MAKER"
            params["price"] = str(float(order.price))

        if order.idempotency_key:
            params["newClientOrderId"] = order.idempotency_key

        data = await self._request("POST", "/api/v3/order", signed=True, params=params)

        logger.info(f"Placed order: {data}")
        return str(data["orderId"])

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel order."""
        try:
            binance_symbol = symbol.replace("-", "")
            if "USD" in binance_symbol and not "USDT" in binance_symbol:
                binance_symbol = binance_symbol.replace("USD", "USDT")

            await self._request("DELETE", "/api/v3/order", signed=True, params={
                "symbol": binance_symbol,
                "orderId": order_id
            })
            logger.info(f"Cancelled order: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False

    async def get_order_status(self, symbol: str, order_id: str) -> OrderStatus:
        """Get order status."""
        try:
            binance_symbol = symbol.replace("-", "")
            if "USD" in binance_symbol and not "USDT" in binance_symbol:
                binance_symbol = binance_symbol.replace("USD", "USDT")

            data = await self._request("GET", "/api/v3/order", signed=True, params={
                "symbol": binance_symbol,
                "orderId": order_id
            })

            status_map = {
                "NEW": OrderStatus.OPEN,
                "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
                "FILLED": OrderStatus.FILLED,
                "CANCELED": OrderStatus.CANCELLED,
                "PENDING_CANCEL": OrderStatus.OPEN,
                "REJECTED": OrderStatus.REJECTED,
                "EXPIRED": OrderStatus.EXPIRED
            }

            return status_map.get(data["status"], OrderStatus.REJECTED)

        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
            return OrderStatus.REJECTED

    async def get_order_fills(self, symbol: str, order_id: str) -> List[OrderFill]:
        """Get fills."""
        # Binance doesn't provide fills per order easily
        # Would need to query trades and match
        return []

    async def get_open_orders(self, symbol: str) -> List[Dict]:
        """Get open orders."""
        try:
            binance_symbol = symbol.replace("-", "")
            if "USD" in binance_symbol and not "USDT" in binance_symbol:
                binance_symbol = binance_symbol.replace("USD", "USDT")

            return await self._request("GET", "/api/v3/openOrders", signed=True, params={
                "symbol": binance_symbol
            })
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades."""
        try:
            binance_symbol = symbol.replace("-", "")
            if "USD" in binance_symbol and not "USDT" in binance_symbol:
                binance_symbol = binance_symbol.replace("USD", "USDT")

            return await self._request("GET", "/api/v3/trades", params={
                "symbol": binance_symbol,
                "limit": limit
            })
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get OHLCV."""
        try:
            binance_symbol = symbol.replace("-", "")
            if "USD" in binance_symbol and not "USDT" in binance_symbol:
                binance_symbol = binance_symbol.replace("USD", "USDT")

            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "1h": "1h",
                "4h": "4h",
                "1d": "1d"
            }

            params = {
                "symbol": binance_symbol,
                "interval": interval_map.get(timeframe, "1m"),
                "limit": limit
            }

            if since:
                params["startTime"] = int(since.timestamp() * 1000)

            data = await self._request("GET", "/api/v3/klines", params=params)

            candles = []
            for candle in data:
                candles.append({
                    "timestamp": datetime.fromtimestamp(candle[0] / 1000),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                })

            return candles

        except Exception as e:
            logger.error(f"Failed to get OHLCV: {e}")
            return []

    def get_fees(self) -> Tuple[Decimal, Decimal]:
        """Get fees."""
        return (Decimal("0.001"), Decimal("0.001"))  # 0.1% maker/taker

    def get_min_notional(self, symbol: str) -> Decimal:
        """Get min notional."""
        return Decimal("10")

    def get_lot_size(self, symbol: str) -> Decimal:
        """Get lot size."""
        return Decimal("0.00001")

    def get_price_precision(self, symbol: str) -> int:
        """Get price precision."""
        return 2
