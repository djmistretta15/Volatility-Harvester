"""
Paper trading service - trades with simulated execution.
"""
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import Optional
import pandas as pd
from app.adapters.fake_exchange import FakeExchange
from app.core.strategy import VolatilityHarvester
from app.core.risk import RiskManager
from app.core.portfolio import Portfolio
from app.core.execution import ExecutionEngine
from app.core.models import StrategyStateData, MarketData
from app.core.enums import StrategyState
from app.data.ingest import DataIngester
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class PaperTrader:
    """
    Paper trading service using fake exchange.
    """

    def __init__(self, initial_capital: Decimal = Decimal("10000")):
        self.exchange = FakeExchange(initial_price=Decimal("50000"))
        self.symbol = settings.symbol
        self.strategy = VolatilityHarvester()
        self.risk_manager = RiskManager()
        self.portfolio = Portfolio(initial_capital)
        self.execution_engine = ExecutionEngine(self.exchange, self.symbol)
        self.data_ingester = DataIngester(self.exchange, self.symbol)

        self.state = StrategyStateData()
        self.state.state = StrategyState.FLAT
        self.state.total_equity = initial_capital
        self.state.peak_equity = initial_capital

        self.running = False
        self.candles_buffer: list = []

    async def start(self):
        """Start paper trading."""
        logger.info("Starting paper trader...")
        await self.exchange.connect()
        self.running = True

        # Initialize balances
        self.exchange.balances["USD"] = self.portfolio.cash
        self.exchange.balances["BTC"] = self.portfolio.btc

        logger.info(f"Paper trader started with ${self.portfolio.cash:.2f}")

        # Start trading loop
        asyncio.create_task(self._trading_loop())

    async def stop(self):
        """Stop paper trading."""
        logger.info("Stopping paper trader...")
        self.running = False
        await self.exchange.disconnect()

    async def _trading_loop(self):
        """Main trading loop."""
        while self.running:
            try:
                # Get current market data
                market_data = await self.exchange.get_ticker(self.symbol)

                # Sync portfolio balances
                self.portfolio.cash = await self.exchange.get_balance("USD")
                self.portfolio.btc = await self.exchange.get_balance("BTC")
                self.portfolio.sync_state(self.state, market_data.mid)

                # Get recent candles for ATR
                candles_df = await self._get_recent_candles(30)

                # Check circuit breakers
                should_pause, cb_reason, reason = self.risk_manager.check_all_circuit_breakers(
                    self.state, market_data, self.exchange.last_heartbeat
                )

                if should_pause and not self.state.paused:
                    logger.warning(f"Circuit breaker triggered: {reason}")
                    self.state.paused = True
                    self.state.pause_reason = reason

                    # Flatten if necessary
                    should_flatten, flatten_reason = self.risk_manager.should_flatten_position(
                        self.state, market_data, self.exchange.last_heartbeat
                    )

                    if should_flatten and self.state.state == StrategyState.LONG:
                        logger.warning(f"Emergency flatten: {flatten_reason}")
                        await self._execute_sell(market_data)

                # Generate signal
                signal = self.strategy.generate_signal(self.state, market_data, candles_df)

                # Execute signal
                if signal.signal_type == "buy" and self.state.state == StrategyState.FLAT and not self.state.paused:
                    await self._execute_buy(market_data)

                elif signal.signal_type == "sell" and self.state.state == StrategyState.LONG:
                    await self._execute_sell(market_data)

                # Log status periodically
                logger.debug(f"State: {self.state.state.value}, Equity: ${self.state.total_equity:.2f}, "
                            f"BTC: {self.portfolio.btc:.8f}, Price: ${market_data.mid:.2f}")

            except Exception as e:
                logger.error(f"Trading loop error: {e}", exc_info=True)

            # Wait before next iteration
            await asyncio.sleep(1)  # Check every second

    async def _execute_buy(self, market_data: MarketData):
        """Execute buy order."""
        try:
            # Calculate position size
            qty = self.strategy.calculate_position_size(
                self.portfolio.cash, market_data.mid
            )

            if qty > 0:
                logger.info(f"Executing BUY: {qty:.8f} BTC @ ${market_data.mid:.2f}")

                success, fill, error = await self.execution_engine.execute_buy(qty, market_data)

                if success and fill:
                    # Update strategy state
                    self.strategy.update_state_after_buy(
                        self.state, fill.price, fill.qty, fill.timestamp
                    )

                    logger.info(f"BUY filled: {fill.qty:.8f} @ ${fill.price:.2f}, fee=${fill.fee:.2f}")
                else:
                    logger.error(f"BUY failed: {error}")

        except Exception as e:
            logger.error(f"Buy execution error: {e}", exc_info=True)

    async def _execute_sell(self, market_data: MarketData):
        """Execute sell order."""
        try:
            qty = self.portfolio.btc

            if qty > 0:
                logger.info(f"Executing SELL: {qty:.8f} BTC @ ${market_data.mid:.2f}")

                success, fill, error = await self.execution_engine.execute_sell(qty, market_data)

                if success and fill:
                    # Calculate PnL
                    if self.state.last_buy_price:
                        entry_cost = self.state.last_buy_price * fill.qty
                        exit_revenue = fill.price * fill.qty - Decimal(str(fill.fee))
                        realized_pnl = exit_revenue - entry_cost
                    else:
                        realized_pnl = Decimal("0")

                    # Update strategy state
                    self.strategy.update_state_after_sell(
                        self.state, fill.price, realized_pnl, fill.timestamp
                    )

                    # Update risk manager
                    self.risk_manager.update_daily_pnl(realized_pnl)

                    logger.info(f"SELL filled: {fill.qty:.8f} @ ${fill.price:.2f}, PnL=${realized_pnl:.2f}")
                else:
                    logger.error(f"SELL failed: {error}")

        except Exception as e:
            logger.error(f"Sell execution error: {e}", exc_info=True)

    async def _get_recent_candles(self, count: int = 30) -> Optional[pd.DataFrame]:
        """Get recent candles for analysis."""
        try:
            # In paper trading, generate from price history
            # Simplified: return None and strategy will use defaults
            return None
        except Exception as e:
            logger.error(f"Failed to get candles: {e}")
            return None

    def get_status(self) -> dict:
        """Get current trading status."""
        return {
            "running": self.running,
            "state": self.state.state.value,
            "paused": self.state.paused,
            "pause_reason": self.state.pause_reason,
            "equity": float(self.state.total_equity),
            "cash": float(self.portfolio.cash),
            "btc": float(self.portfolio.btc),
            "realized_pnl": float(self.state.realized_pnl),
            "unrealized_pnl": float(self.state.unrealized_pnl),
            "total_trades": self.state.total_trades,
            "win_rate": (self.state.winning_trades / self.state.total_trades * 100) if self.state.total_trades > 0 else 0,
            "drawdown_pct": float(self.state.current_drawdown_pct)
        }
