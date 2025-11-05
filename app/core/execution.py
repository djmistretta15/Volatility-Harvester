"""
Execution engine - handles order placement, fills, and order lifecycle.
"""
from decimal import Decimal
from typing import Optional, Tuple
from datetime import datetime
import asyncio
import uuid
from app.adapters.exchange_base import ExchangeAdapter
from app.core.models import OrderRequest, OrderFill, MarketData, Signal
from app.core.enums import Side, OrderType, OrderStatus
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Handles order execution with maker-first logic and fallback to taker.

    Order flow:
    1. Try to place limit order inside spread (maker)
    2. Wait for fill with timeout
    3. If not filled, cancel and retry as taker (market)
    """

    def __init__(self, exchange: ExchangeAdapter, symbol: str):
        self.exchange = exchange
        self.symbol = symbol
        self.maker_fee_pct = settings.maker_fee_pct / Decimal("100")
        self.taker_fee_pct = settings.taker_fee_pct / Decimal("100")

    def calculate_fee(self, notional: Decimal, is_maker: bool) -> Decimal:
        """Calculate trading fee."""
        fee_pct = self.maker_fee_pct if is_maker else self.taker_fee_pct
        return notional * fee_pct

    async def execute_buy(
        self,
        qty: Decimal,
        market_data: MarketData,
        maker_first: bool = True
    ) -> Tuple[bool, Optional[OrderFill], Optional[str]]:
        """
        Execute a buy order.

        Args:
            qty: Quantity to buy
            market_data: Current market data
            maker_first: Try maker order first

        Returns:
            (success, fill, error_message)
        """
        # Validate and round quantity
        qty = self.exchange.round_quantity(self.symbol, qty)
        min_notional = self.exchange.get_min_notional(self.symbol)

        notional = qty * market_data.ask
        if notional < min_notional:
            return (False, None, f"Order size ${notional:.2f} below minimum ${min_notional:.2f}")

        if maker_first and settings.maker_first:
            # Try limit order at bid (inside spread)
            limit_price = market_data.bid + (market_data.ask - market_data.bid) * Decimal("0.25")  # 25% into spread
            limit_price = self.exchange.round_price(self.symbol, limit_price)

            logger.info(f"Attempting maker buy: {qty:.8f} @ ${limit_price:.2f}")

            order = OrderRequest(
                side=Side.BUY,
                order_type=OrderType.POST_ONLY,
                qty=qty,
                price=limit_price,
                post_only=True,
                timeout_seconds=settings.order_timeout_seconds,
                idempotency_key=f"buy_{uuid.uuid4().hex[:16]}"
            )

            try:
                order_id = await self.exchange.place_order(self.symbol, order)

                # Wait for fill
                fill = await self._wait_for_fill(order_id, order.timeout_seconds)

                if fill is not None:
                    logger.info(f"Maker buy filled: {fill.qty:.8f} @ ${fill.price:.2f}")
                    return (True, fill, None)

                # Not filled, cancel
                logger.warning("Maker order not filled, cancelling...")
                await self.exchange.cancel_order(self.symbol, order_id)

            except Exception as e:
                logger.error(f"Maker order failed: {e}")
                # Fall through to taker

        # Fallback to taker (market order)
        logger.info(f"Executing taker buy: {qty:.8f} @ market")

        # Estimate price with slippage
        estimated_price = market_data.ask * (Decimal("1") + settings.taker_slippage_bps / Decimal("10000"))

        order = OrderRequest(
            side=Side.BUY,
            order_type=OrderType.MARKET,
            qty=qty,
            price=estimated_price,  # For notional calculation
            idempotency_key=f"buy_mkt_{uuid.uuid4().hex[:16]}"
        )

        try:
            order_id = await self.exchange.place_order(self.symbol, order)

            # Wait for fill
            fill = await self._wait_for_fill(order_id, timeout=10)

            if fill is not None:
                logger.info(f"Taker buy filled: {fill.qty:.8f} @ ${fill.price:.2f}")
                return (True, fill, None)
            else:
                return (False, None, "Market order failed to fill")

        except Exception as e:
            error_msg = f"Buy execution failed: {e}"
            logger.error(error_msg)
            return (False, None, error_msg)

    async def execute_sell(
        self,
        qty: Decimal,
        market_data: MarketData,
        maker_first: bool = True
    ) -> Tuple[bool, Optional[OrderFill], Optional[str]]:
        """
        Execute a sell order.

        Args:
            qty: Quantity to sell
            market_data: Current market data
            maker_first: Try maker order first

        Returns:
            (success, fill, error_message)
        """
        # Validate and round quantity
        qty = self.exchange.round_quantity(self.symbol, qty)
        min_notional = self.exchange.get_min_notional(self.symbol)

        notional = qty * market_data.bid
        if notional < min_notional:
            return (False, None, f"Order size ${notional:.2f} below minimum ${min_notional:.2f}")

        if maker_first and settings.maker_first:
            # Try limit order at ask (inside spread)
            limit_price = market_data.ask - (market_data.ask - market_data.bid) * Decimal("0.25")  # 25% into spread
            limit_price = self.exchange.round_price(self.symbol, limit_price)

            logger.info(f"Attempting maker sell: {qty:.8f} @ ${limit_price:.2f}")

            order = OrderRequest(
                side=Side.SELL,
                order_type=OrderType.POST_ONLY,
                qty=qty,
                price=limit_price,
                post_only=True,
                timeout_seconds=settings.order_timeout_seconds,
                idempotency_key=f"sell_{uuid.uuid4().hex[:16]}"
            )

            try:
                order_id = await self.exchange.place_order(self.symbol, order)

                # Wait for fill
                fill = await self._wait_for_fill(order_id, order.timeout_seconds)

                if fill is not None:
                    logger.info(f"Maker sell filled: {fill.qty:.8f} @ ${fill.price:.2f}")
                    return (True, fill, None)

                # Not filled, cancel
                logger.warning("Maker order not filled, cancelling...")
                await self.exchange.cancel_order(self.symbol, order_id)

            except Exception as e:
                logger.error(f"Maker order failed: {e}")
                # Fall through to taker

        # Fallback to taker (market order)
        logger.info(f"Executing taker sell: {qty:.8f} @ market")

        # Estimate price with slippage
        estimated_price = market_data.bid * (Decimal("1") - settings.taker_slippage_bps / Decimal("10000"))

        order = OrderRequest(
            side=Side.SELL,
            order_type=OrderType.MARKET,
            qty=qty,
            price=estimated_price,  # For notional calculation
            idempotency_key=f"sell_mkt_{uuid.uuid4().hex[:16]}"
        )

        try:
            order_id = await self.exchange.place_order(self.symbol, order)

            # Wait for fill
            fill = await self._wait_for_fill(order_id, timeout=10)

            if fill is not None:
                logger.info(f"Taker sell filled: {fill.qty:.8f} @ ${fill.price:.2f}")
                return (True, fill, None)
            else:
                return (False, None, "Market order failed to fill")

        except Exception as e:
            error_msg = f"Sell execution failed: {e}"
            logger.error(error_msg)
            return (False, None, error_msg)

    async def _wait_for_fill(self, order_id: str, timeout: int = 30) -> Optional[OrderFill]:
        """
        Wait for order to fill.

        Args:
            order_id: Order ID to wait for
            timeout: Timeout in seconds

        Returns:
            OrderFill if filled, None otherwise
        """
        start_time = datetime.utcnow()
        check_interval = 0.5  # Check every 500ms

        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            status = await self.exchange.get_order_status(self.symbol, order_id)

            if status == OrderStatus.FILLED:
                fills = await self.exchange.get_order_fills(self.symbol, order_id)
                if fills:
                    return fills[0]  # Return first fill (typically only one for spot)
                else:
                    # Create synthetic fill from order status
                    logger.warning("Order filled but no fills returned, creating synthetic")
                    return None

            elif status in [OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]:
                logger.warning(f"Order {order_id} ended with status {status}")
                return None

            await asyncio.sleep(check_interval)

        logger.warning(f"Order {order_id} timed out after {timeout}s")
        return None

    async def execute_signal(
        self,
        signal: Signal,
        qty: Decimal,
        market_data: MarketData
    ) -> Tuple[bool, Optional[OrderFill], Optional[str]]:
        """
        Execute a trading signal.

        Args:
            signal: Trading signal
            qty: Quantity to trade
            market_data: Current market data

        Returns:
            (success, fill, error_message)
        """
        if signal.signal_type == "buy":
            return await self.execute_buy(qty, market_data)
        elif signal.signal_type == "sell":
            return await self.execute_sell(qty, market_data)
        else:
            return (False, None, f"Invalid signal type: {signal.signal_type}")
