"""
Coinbase Advanced Trade API adapter.
"""
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import hmac
import hashlib
import time
import json
import aiohttp
from app.adapters.exchange_base import ExchangeAdapter
from app.core.models import MarketData, OrderRequest, OrderFill
from app.core.enums import OrderStatus, Side, OrderType
import logging

logger = logging.getLogger(__name__)


class CoinbaseAdapter(ExchangeAdapter):
    """
    Coinbase Advanced Trade API adapter.
    Uses REST API for orders and account data.
    """

    BASE_URL = "https://api.coinbase.com"

    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)
        self.session: Optional[aiohttp.ClientSession] = None

    def _generate_signature(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Generate request signature for Coinbase."""
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _get_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Get headers for authenticated request."""
        timestamp = str(int(time.time()))
        signature = self._generate_signature(timestamp, method, path, body)

        return {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }

    async def connect(self):
        """Connect (create session)."""
        self.session = aiohttp.ClientSession()
        self.connected = True
        self.last_heartbeat = datetime.utcnow()
        logger.info("Connected to Coinbase")

    async def disconnect(self):
        """Disconnect."""
        if self.session:
            await self.session.close()
        self.connected = False
        logger.info("Disconnected from Coinbase")

    async def _request(self, method: str, path: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """Make authenticated request."""
        if not self.session:
            raise RuntimeError("Not connected")

        url = f"{self.BASE_URL}{path}"
        body = json.dumps(data) if data else ""
        headers = self._get_headers(method, path, body)

        async with self.session.request(method, url, headers=headers, params=params, json=data) as response:
            self.last_heartbeat = datetime.utcnow()
            response.raise_for_status()
            return await response.json()

    async def get_ticker(self, symbol: str) -> MarketData:
        """Get current market data."""
        # Convert symbol format: BTC-USD is correct for Coinbase
        data = await self._request("GET", f"/api/v3/brokerage/products/{symbol}/ticker")

        return MarketData(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            bid=Decimal(data.get("bid", "0")),
            ask=Decimal(data.get("ask", "0")),
            last=Decimal(data.get("price", "0"))
        )

    async def get_balance(self, asset: str) -> Decimal:
        """Get balance for asset."""
        accounts = await self._request("GET", "/api/v3/brokerage/accounts")

        for account in accounts.get("accounts", []):
            if account["currency"] == asset:
                return Decimal(account["available_balance"]["value"])

        return Decimal("0")

    async def get_balances(self) -> Dict[str, Decimal]:
        """Get all balances."""
        accounts = await self._request("GET", "/api/v3/brokerage/accounts")

        balances = {}
        for account in accounts.get("accounts", []):
            currency = account["currency"]
            balance = Decimal(account["available_balance"]["value"])
            if balance > 0:
                balances[currency] = balance

        return balances

    async def place_order(self, symbol: str, order: OrderRequest) -> str:
        """Place an order."""
        order_config = {}

        if order.order_type == OrderType.MARKET:
            if order.side == Side.BUY:
                order_config = {
                    "market_market_ioc": {
                        "quote_size": str(float(order.qty * order.price)) if order.price else str(float(order.qty))
                    }
                }
            else:
                order_config = {
                    "market_market_ioc": {
                        "base_size": str(float(order.qty))
                    }
                }
        elif order.order_type == OrderType.LIMIT or order.order_type == OrderType.POST_ONLY:
            order_config = {
                "limit_limit_gtc" if order.order_type == OrderType.LIMIT else "limit_limit_gtd": {
                    "base_size": str(float(order.qty)),
                    "limit_price": str(float(order.price)),
                    "post_only": order.post_only
                }
            }

        data = {
            "client_order_id": order.idempotency_key or f"order_{int(time.time() * 1000)}",
            "product_id": symbol,
            "side": order.side.value.upper(),
            "order_configuration": order_config
        }

        response = await self._request("POST", "/api/v3/brokerage/orders", data=data)

        logger.info(f"Placed order: {response}")
        return response.get("order_id", "")

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order."""
        try:
            await self._request("POST", f"/api/v3/brokerage/orders/batch_cancel", data={"order_ids": [order_id]})
            logger.info(f"Cancelled order: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def get_order_status(self, symbol: str, order_id: str) -> OrderStatus:
        """Get order status."""
        try:
            data = await self._request("GET", f"/api/v3/brokerage/orders/historical/{order_id}")

            status = data.get("order", {}).get("status", "").upper()

            status_map = {
                "PENDING": OrderStatus.PENDING,
                "OPEN": OrderStatus.OPEN,
                "FILLED": OrderStatus.FILLED,
                "CANCELLED": OrderStatus.CANCELLED,
                "EXPIRED": OrderStatus.EXPIRED,
                "FAILED": OrderStatus.REJECTED,
                "QUEUED": OrderStatus.PENDING
            }

            return status_map.get(status, OrderStatus.REJECTED)

        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            return OrderStatus.REJECTED

    async def get_order_fills(self, symbol: str, order_id: str) -> List[OrderFill]:
        """Get fills for order."""
        try:
            data = await self._request("GET", "/api/v3/brokerage/orders/historical/fills", params={"order_id": order_id})

            fills = []
            for fill in data.get("fills", []):
                fills.append(OrderFill(
                    order_id=order_id,
                    timestamp=datetime.fromisoformat(fill["trade_time"].replace("Z", "+00:00")),
                    side=Side.BUY if fill["side"] == "BUY" else Side.SELL,
                    qty=Decimal(fill["size"]),
                    price=Decimal(fill["price"]),
                    fee=Decimal(fill.get("commission", "0")),
                    fee_asset=symbol.split("-")[1]  # USD for BTC-USD
                ))

            return fills

        except Exception as e:
            logger.error(f"Failed to get fills for {order_id}: {e}")
            return []

    async def get_open_orders(self, symbol: str) -> List[Dict]:
        """Get open orders."""
        try:
            data = await self._request("GET", "/api/v3/brokerage/orders/historical/batch", params={"product_id": symbol})
            return data.get("orders", [])
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades."""
        try:
            data = await self._request("GET", f"/api/v3/brokerage/products/{symbol}/ticker")
            # Coinbase doesn't provide trade history easily, return empty
            return []
        except Exception as e:
            logger.error(f"Failed to get recent trades: {e}")
            return []

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get OHLCV candles."""
        try:
            # Map timeframe to granularity in seconds
            granularity_map = {
                "1m": 60,
                "5m": 300,
                "15m": 900,
                "1h": 3600,
                "6h": 21600,
                "1d": 86400
            }

            granularity = granularity_map.get(timeframe, 60)

            params = {
                "granularity": granularity,
            }

            if since:
                params["start"] = int(since.timestamp())
                params["end"] = int(datetime.utcnow().timestamp())

            data = await self._request("GET", f"/api/v3/brokerage/products/{symbol}/candles", params=params)

            candles = []
            for candle in data.get("candles", [])[:limit]:
                candles.append({
                    "timestamp": datetime.fromtimestamp(int(candle["start"])),
                    "open": float(candle["open"]),
                    "high": float(candle["high"]),
                    "low": float(candle["low"]),
                    "close": float(candle["close"]),
                    "volume": float(candle["volume"])
                })

            return sorted(candles, key=lambda x: x["timestamp"])

        except Exception as e:
            logger.error(f"Failed to get OHLCV: {e}")
            return []

    def get_fees(self) -> Tuple[Decimal, Decimal]:
        """Get fees (Coinbase Advanced defaults)."""
        # These can vary by volume tier
        return (Decimal("0.004"), Decimal("0.006"))  # 0.4% maker, 0.6% taker

    def get_min_notional(self, symbol: str) -> Decimal:
        """Get minimum notional."""
        return Decimal("10")  # $10 minimum for Coinbase

    def get_lot_size(self, symbol: str) -> Decimal:
        """Get lot size."""
        if "BTC" in symbol:
            return Decimal("0.00001")  # 0.00001 BTC
        return Decimal("0.01")

    def get_price_precision(self, symbol: str) -> int:
        """Get price precision."""
        return 2  # $0.01 for USD pairs
