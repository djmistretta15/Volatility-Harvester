"""
Portfolio management - tracks positions, balances, and equity.
"""
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime
from app.core.models import StrategyStateData
import logging

logger = logging.getLogger(__name__)


class Portfolio:
    """
    Portfolio manager.

    Tracks:
    - Cash balance
    - BTC position
    - Total equity
    - Unrealized PnL
    - Realized PnL
    """

    def __init__(self, initial_cash: Decimal, initial_btc: Decimal = Decimal("0")):
        self.cash = initial_cash
        self.btc = initial_btc
        self.initial_equity = initial_cash
        self.realized_pnl = Decimal("0")

    def get_equity(self, btc_price: Decimal) -> Decimal:
        """Calculate total equity (cash + BTC value)."""
        return self.cash + (self.btc * btc_price)

    def get_unrealized_pnl(self, btc_price: Decimal) -> Decimal:
        """Calculate unrealized PnL (BTC position value change)."""
        btc_value = self.btc * btc_price
        # Unrealized PnL is current equity minus initial equity minus realized PnL
        current_equity = self.get_equity(btc_price)
        return current_equity - self.initial_equity - self.realized_pnl

    def execute_buy(self, qty: Decimal, price: Decimal, fee: Decimal) -> Decimal:
        """
        Execute buy (convert cash to BTC).

        Args:
            qty: BTC quantity
            price: Price per BTC
            fee: Fee in USD

        Returns:
            Total cost (notional + fee)
        """
        cost = qty * price
        total_cost = cost + fee

        if self.cash < total_cost:
            raise ValueError(f"Insufficient cash: have ${self.cash:.2f}, need ${total_cost:.2f}")

        self.cash -= total_cost
        self.btc += qty

        logger.info(f"Buy executed: {qty:.8f} BTC @ ${price:.2f}, cost=${total_cost:.2f} (fee=${fee:.2f})")
        return total_cost

    def execute_sell(self, qty: Decimal, price: Decimal, fee: Decimal) -> Decimal:
        """
        Execute sell (convert BTC to cash).

        Args:
            qty: BTC quantity
            price: Price per BTC
            fee: Fee in USD

        Returns:
            Net proceeds (revenue - fee)
        """
        if self.btc < qty:
            raise ValueError(f"Insufficient BTC: have {self.btc:.8f}, need {qty:.8f}")

        revenue = qty * price
        net_proceeds = revenue - fee

        self.btc -= qty
        self.cash += net_proceeds

        # Update realized PnL
        # This is simplified - in reality would track cost basis per position
        self.realized_pnl += net_proceeds - (qty * price)  # Simplified

        logger.info(f"Sell executed: {qty:.8f} BTC @ ${price:.2f}, proceeds=${net_proceeds:.2f} (fee=${fee:.2f})")
        return net_proceeds

    def get_balances(self) -> Dict[str, Decimal]:
        """Get current balances."""
        return {
            "USD": self.cash,
            "BTC": self.btc
        }

    def sync_state(self, state: StrategyStateData, btc_price: Decimal):
        """Sync portfolio data to strategy state."""
        state.total_equity = self.get_equity(btc_price)
        state.unrealized_pnl = self.get_unrealized_pnl(btc_price)
        state.realized_pnl = self.realized_pnl
        state.current_position_qty = self.btc

        # Update peak equity and drawdown
        if state.total_equity > state.peak_equity:
            state.peak_equity = state.total_equity

        if state.peak_equity > 0:
            dd_pct = ((state.peak_equity - state.total_equity) / state.peak_equity) * Decimal("100")
            state.current_drawdown_pct = dd_pct
        else:
            state.current_drawdown_pct = Decimal("0")

    def to_dict(self, btc_price: Decimal) -> Dict:
        """Export portfolio snapshot."""
        return {
            "cash_usd": float(self.cash),
            "btc_qty": float(self.btc),
            "btc_value_usd": float(self.btc * btc_price),
            "total_equity": float(self.get_equity(btc_price)),
            "realized_pnl": float(self.realized_pnl),
            "unrealized_pnl": float(self.get_unrealized_pnl(btc_price)),
            "total_pnl": float(self.realized_pnl + self.get_unrealized_pnl(btc_price))
        }
