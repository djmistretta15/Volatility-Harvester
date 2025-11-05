"""
Fake exchange adapter for testing and paper trading.
"""
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import asyncio
from app.adapters.exchange_base import ExchangeAdapter
from app.core.models import MarketData, OrderRequest, OrderFill
from app.core.enums import OrderStatus, Side, OrderType
import random


class FakeExchange(ExchangeAdapter):
    """
    Simulated exchange for testing.
    Maintains an order book, simulates fills with realistic behavior.
    """

    def __init__(self, api_key: str = "", api_secret: str = "", initial_price: Decimal = Decimal("50000")):
        super().__init__(api_key, api_secret)
        self.current_price = initial_price
        self.balances: Dict[str, Decimal] = {
            "USD": Decimal("10000"),
            "BTC": Decimal("0")
        }
        self.orders: Dict[str, Dict] = {}
        self.fills: Dict[str, List[OrderFill]] = {}
        self.trades: List[Dict] = []
        self.maker_fee = Decimal("0.001")  # 0.1%
        self.taker_fee = Decimal("0.003")  # 0.3%
        self.spread_bps = Decimal("5")  # 5 bps spread
        self.price_volatility = Decimal("0.02")  # 2% price volatility

    async def connect(self):
        """Connect (instant for fake exchange)."""
        self.connected = True
        self.last_heartbeat = datetime.utcnow()
        # Start price simulation
        asyncio.create_task(self._simulate_price_movement())

    async def disconnect(self):
        """Disconnect."""
        self.connected = False

    async def _simulate_price_movement(self):
        """Simulate realistic price movement."""
        while self.connected:
            # Random walk with drift
            change = random.gauss(0, float(self.price_volatility / 100))
            self.current_price *= Decimal(str(1 + change))
            self.last_heartbeat = datetime.utcnow()

            # Check if any limit orders should fill
            await self._process_limit_orders()

            await asyncio.sleep(0.1)  # Update every 100ms

    async def _process_limit_orders(self):
        """Process limit orders that should fill at current price."""
        for order_id, order in list(self.orders.items()):
            if order["status"] != OrderStatus.OPEN:
                continue

            should_fill = False
            if order["side"] == Side.BUY and self.current_price <= order["price"]:
                should_fill = True
            elif order["side"] == Side.SELL and self.current_price >= order["price"]:
                should_fill = True

            if should_fill:
                await self._fill_order(order_id, order)

    async def _fill_order(self, order_id: str, order: Dict):
        """Fill an order."""
        qty = order["qty"]
        price = order.get("price", self.current_price)
        side = order["side"]
        is_maker = order["order_type"] != OrderType.MARKET

        # Calculate fee
        fee_rate = self.maker_fee if is_maker else self.taker_fee

        if side == Side.BUY:
            cost = qty * price
            fee = cost * fee_rate
            total_cost = cost + fee

            if self.balances.get("USD", Decimal("0")) >= total_cost:
                self.balances["USD"] -= total_cost
                self.balances["BTC"] = self.balances.get("BTC", Decimal("0")) + qty

                # Create fill
                fill = OrderFill(
                    order_id=order_id,
                    timestamp=datetime.utcnow(),
                    side=side,
                    qty=qty,
                    price=price,
                    fee=fee,
                    fee_asset="USD"
                )

                if order_id not in self.fills:
                    self.fills[order_id] = []
                self.fills[order_id].append(fill)

                order["status"] = OrderStatus.FILLED
                order["filled_qty"] = qty
                order["filled_price"] = price
            else:
                order["status"] = OrderStatus.REJECTED

        elif side == Side.SELL:
            if self.balances.get("BTC", Decimal("0")) >= qty:
                revenue = qty * price
                fee = revenue * fee_rate
                net_revenue = revenue - fee

                self.balances["BTC"] -= qty
                self.balances["USD"] = self.balances.get("USD", Decimal("0")) + net_revenue

                # Create fill
                fill = OrderFill(
                    order_id=order_id,
                    timestamp=datetime.utcnow(),
                    side=side,
                    qty=qty,
                    price=price,
                    fee=fee,
                    fee_asset="USD"
                )

                if order_id not in self.fills:
                    self.fills[order_id] = []
                self.fills[order_id].append(fill)

                order["status"] = OrderStatus.FILLED
                order["filled_qty"] = qty
                order["filled_price"] = price
            else:
                order["status"] = OrderStatus.REJECTED

    async def get_ticker(self, symbol: str) -> MarketData:
        """Get current market data."""
        spread = self.current_price * (self.spread_bps / Decimal("10000"))
        return MarketData(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            bid=self.current_price - spread / 2,
            ask=self.current_price + spread / 2,
            last=self.current_price
        )

    async def get_balance(self, asset: str) -> Decimal:
        """Get balance for asset."""
        return self.balances.get(asset, Decimal("0"))

    async def get_balances(self) -> Dict[str, Decimal]:
        """Get all balances."""
        return self.balances.copy()

    async def place_order(self, symbol: str, order: OrderRequest) -> str:
        """Place an order."""
        order_id = str(uuid.uuid4())

        order_dict = {
            "id": order_id,
            "symbol": symbol,
            "side": order.side,
            "order_type": order.order_type,
            "qty": order.qty,
            "price": order.price,
            "status": OrderStatus.PENDING,
            "filled_qty": Decimal("0"),
            "filled_price": None,
            "created_at": datetime.utcnow()
        }

        self.orders[order_id] = order_dict

        # Process market orders immediately
        if order.order_type == OrderType.MARKET:
            order_dict["status"] = OrderStatus.OPEN
            await self._fill_order(order_id, order_dict)
        else:
            order_dict["status"] = OrderStatus.OPEN

        return order_id

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order."""
        if order_id in self.orders:
            if self.orders[order_id]["status"] == OrderStatus.OPEN:
                self.orders[order_id]["status"] = OrderStatus.CANCELLED
                return True
        return False

    async def get_order_status(self, symbol: str, order_id: str) -> OrderStatus:
        """Get order status."""
        if order_id in self.orders:
            return self.orders[order_id]["status"]
        return OrderStatus.REJECTED

    async def get_order_fills(self, symbol: str, order_id: str) -> List[OrderFill]:
        """Get fills for order."""
        return self.fills.get(order_id, [])

    async def get_open_orders(self, symbol: str) -> List[Dict]:
        """Get open orders."""
        return [
            order for order in self.orders.values()
            if order["status"] in [OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]
            and order["symbol"] == symbol
        ]

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades."""
        return self.trades[-limit:]

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get OHLCV data (simulated)."""
        # For testing, generate some random candles
        candles = []
        current_time = since or datetime.utcnow() - timedelta(hours=limit)
        current_price = self.current_price

        for i in range(limit):
            # Random candle
            open_price = current_price
            change = random.gauss(0, 0.01)  # 1% volatility
            close_price = open_price * Decimal(str(1 + change))
            high_price = max(open_price, close_price) * Decimal("1.002")
            low_price = min(open_price, close_price) * Decimal("0.998")

            candles.append({
                "timestamp": current_time,
                "open": float(open_price),
                "high": float(high_price),
                "low": float(low_price),
                "close": float(close_price),
                "volume": random.uniform(1, 10)
            })

            current_time += timedelta(minutes=1)
            current_price = close_price

        return candles

    def get_fees(self) -> Tuple[Decimal, Decimal]:
        """Get fees."""
        return (self.maker_fee, self.taker_fee)

    def get_min_notional(self, symbol: str) -> Decimal:
        """Get minimum notional."""
        return Decimal("10")

    def get_lot_size(self, symbol: str) -> Decimal:
        """Get lot size."""
        return Decimal("0.00001")

    def get_price_precision(self, symbol: str) -> int:
        """Get price precision."""
        return 2
