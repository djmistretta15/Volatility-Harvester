"""
Live trading service - real money trading.
"""
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import Optional
import pandas as pd
from app.adapters.coinbase import CoinbaseAdapter
from app.adapters.binance import BinanceAdapter
from app.core.strategy import VolatilityHarvester
from app.core.risk import RiskManager
from app.core.portfolio import Portfolio
from app.core.execution import ExecutionEngine
from app.core.models import StrategyStateData
from app.core.enums import StrategyState
from app.data.ingest import DataIngester
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class LiveTrader:
    """
    Live trading service with real exchange.

    WARNING: Trades with real money. Use with caution.
    """

    def __init__(self):
        # Initialize exchange adapter
        if settings.exchange == "coinbase":
            self.exchange = CoinbaseAdapter(
                settings.coinbase_api_key,
                settings.coinbase_api_secret
            )
        elif settings.exchange == "binance":
            self.exchange = BinanceAdapter(
                settings.binance_api_key,
                settings.binance_api_secret
            )
        else:
            raise ValueError(f"Unsupported exchange: {settings.exchange}")

        self.symbol = settings.symbol
        self.strategy = VolatilityHarvester()
        self.risk_manager = RiskManager()
        self.execution_engine = ExecutionEngine(self.exchange, self.symbol)
        self.data_ingester = DataIngester(self.exchange, self.symbol)

        self.state = StrategyStateData()
        self.state.state = StrategyState.FLAT

        self.portfolio: Optional[Portfolio] = None
        self.running = False

    async def start(self):
        """Start live trading."""
        logger.warning("=" * 60)
        logger.warning("STARTING LIVE TRADING - REAL MONEY AT RISK")
        logger.warning("=" * 60)

        await self.exchange.connect()

        # Get initial balances
        balances = await self.exchange.get_balances()
        cash = balances.get("USD", Decimal("0"))
        btc = balances.get("BTC", Decimal("0"))

        logger.info(f"Initial balances: ${cash:.2f} USD, {btc:.8f} BTC")

        # Get current price
        ticker = await self.exchange.get_ticker(self.symbol)
        btc_value = btc * ticker.mid
        total_equity = cash + btc_value

        # Initialize portfolio
        self.portfolio = Portfolio(cash, btc)
        self.state.total_equity = total_equity
        self.state.peak_equity = total_equity

        # Determine initial state
        if btc > Decimal("0.0001"):  # Has BTC position
            self.state.state = StrategyState.LONG
            self.state.current_position_qty = btc
            logger.info(f"Starting in LONG state with {btc:.8f} BTC")
        else:
            self.state.state = StrategyState.FLAT
            logger.info("Starting in FLAT state")

        self.running = True
        logger.info("Live trader started")

        # Start trading loop
        asyncio.create_task(self._trading_loop())

    async def stop(self):
        """Stop live trading."""
        logger.warning("Stopping live trader...")
        self.running = False
        await self.exchange.disconnect()
        logger.info("Live trader stopped")

    async def emergency_flatten(self):
        """Emergency position flatten (market sell)."""
        logger.critical("EMERGENCY FLATTEN TRIGGERED")

        if self.state.state == StrategyState.LONG:
            btc = await self.exchange.get_balance("BTC")

            if btc > Decimal("0.0001"):
                logger.critical(f"Flattening {btc:.8f} BTC at market")

                try:
                    market_data = await self.exchange.get_ticker(self.symbol)
                    success, fill, error = await self.execution_engine.execute_sell(
                        btc, market_data, maker_first=False  # Force market order
                    )

                    if success:
                        logger.critical(f"Emergency flatten complete: {fill.qty:.8f} @ ${fill.price:.2f}")
                    else:
                        logger.error(f"Emergency flatten failed: {error}")

                except Exception as e:
                    logger.error(f"Emergency flatten error: {e}", exc_info=True)

    async def _trading_loop(self):
        """Main trading loop."""
        while self.running:
            try:
                # Get current market data
                market_data = await self.exchange.get_ticker(self.symbol)

                # Update portfolio from exchange
                balances = await self.exchange.get_balances()
                self.portfolio.cash = balances.get("USD", Decimal("0"))
                self.portfolio.btc = balances.get("BTC", Decimal("0"))
                self.portfolio.sync_state(self.state, market_data.mid)

                # Get recent candles
                candles_df = await self._get_recent_candles()

                # Check circuit breakers
                should_pause, cb_reason, reason = self.risk_manager.check_all_circuit_breakers(
                    self.state, market_data, self.exchange.last_heartbeat
                )

                if should_pause and not self.state.paused:
                    logger.warning(f"Circuit breaker triggered: {reason}")
                    self.state.paused = True
                    self.state.pause_reason = reason

                    # Check if should flatten
                    should_flatten, flatten_reason = self.risk_manager.should_flatten_position(
                        self.state, market_data, self.exchange.last_heartbeat
                    )

                    if should_flatten:
                        logger.critical(f"Emergency flatten triggered: {flatten_reason}")
                        await self.emergency_flatten()

                # Generate signal
                signal = self.strategy.generate_signal(self.state, market_data, candles_df)

                # Execute signal
                if signal.signal_type == "buy" and self.state.state == StrategyState.FLAT and not self.state.paused:
                    await self._execute_buy(market_data)

                elif signal.signal_type == "sell" and self.state.state == StrategyState.LONG:
                    await self._execute_sell(market_data)

                # Log status
                logger.info(f"[{datetime.utcnow()}] State: {self.state.state.value}, "
                           f"Equity: ${self.state.total_equity:.2f}, "
                           f"BTC: {self.portfolio.btc:.8f}, Price: ${market_data.mid:.2f}")

            except Exception as e:
                logger.error(f"Trading loop error: {e}", exc_info=True)

            # Wait before next iteration (5 seconds for live)
            await asyncio.sleep(5)

    async def _execute_buy(self, market_data):
        """Execute buy."""
        try:
            qty = self.strategy.calculate_position_size(
                self.portfolio.cash, market_data.mid
            )

            if qty > 0:
                logger.info(f"Executing LIVE BUY: {qty:.8f} BTC @ ${market_data.mid:.2f}")

                success, fill, error = await self.execution_engine.execute_buy(qty, market_data)

                if success and fill:
                    self.strategy.update_state_after_buy(
                        self.state, fill.price, fill.qty, fill.timestamp
                    )
                    logger.info(f"BUY filled: {fill.qty:.8f} @ ${fill.price:.2f}")
                else:
                    logger.error(f"BUY failed: {error}")

        except Exception as e:
            logger.error(f"Buy execution error: {e}", exc_info=True)

    async def _execute_sell(self, market_data):
        """Execute sell."""
        try:
            qty = self.portfolio.btc

            if qty > 0:
                logger.info(f"Executing LIVE SELL: {qty:.8f} BTC @ ${market_data.mid:.2f}")

                success, fill, error = await self.execution_engine.execute_sell(qty, market_data)

                if success and fill:
                    # Calculate PnL
                    if self.state.last_buy_price:
                        entry_cost = self.state.last_buy_price * fill.qty
                        exit_revenue = fill.price * fill.qty - Decimal(str(fill.fee))
                        realized_pnl = exit_revenue - entry_cost
                    else:
                        realized_pnl = Decimal("0")

                    self.strategy.update_state_after_sell(
                        self.state, fill.price, realized_pnl, fill.timestamp
                    )

                    self.risk_manager.update_daily_pnl(realized_pnl)

                    logger.info(f"SELL filled: {fill.qty:.8f} @ ${fill.price:.2f}, PnL=${realized_pnl:.2f}")
                else:
                    logger.error(f"SELL failed: {error}")

        except Exception as e:
            logger.error(f"Sell execution error: {e}", exc_info=True)

    async def _get_recent_candles(self, count: int = 30) -> Optional[pd.DataFrame]:
        """Get recent candles."""
        try:
            raw_candles = await self.exchange.get_ohlcv(
                self.symbol, "1m", limit=count
            )

            if raw_candles:
                df = pd.DataFrame(raw_candles)
                return df

            return None
        except Exception as e:
            logger.error(f"Failed to get candles: {e}")
            return None

    def get_status(self) -> dict:
        """Get trading status."""
        return {
            "running": self.running,
            "exchange": settings.exchange,
            "symbol": self.symbol,
            "state": self.state.state.value,
            "paused": self.state.paused,
            "pause_reason": self.state.pause_reason,
            "equity": float(self.state.total_equity),
            "cash": float(self.portfolio.cash) if self.portfolio else 0,
            "btc": float(self.portfolio.btc) if self.portfolio else 0,
            "realized_pnl": float(self.state.realized_pnl),
            "unrealized_pnl": float(self.state.unrealized_pnl),
            "total_trades": self.state.total_trades,
            "win_rate": (self.state.winning_trades / self.state.total_trades * 100) if self.state.total_trades > 0 else 0,
            "drawdown_pct": float(self.state.current_drawdown_pct)
        }
