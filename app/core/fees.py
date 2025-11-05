"""
Fee calculation utilities.
"""
from decimal import Decimal
from typing import Tuple
from app.core.config import settings


def calculate_trading_fee(notional: Decimal, is_maker: bool = True) -> Decimal:
    """
    Calculate trading fee for a given notional value.

    Args:
        notional: Trade notional value in USD
        is_maker: True if maker order, False if taker

    Returns:
        Fee amount in USD
    """
    fee_pct = settings.maker_fee_pct if is_maker else settings.taker_fee_pct
    return notional * (fee_pct / Decimal("100"))


def calculate_round_trip_cost(
    entry_price: Decimal,
    qty: Decimal,
    maker_entry: bool = True,
    maker_exit: bool = True
) -> Tuple[Decimal, Decimal]:
    """
    Calculate round-trip trading costs (entry + exit fees).

    Args:
        entry_price: Entry price
        qty: Quantity
        maker_entry: Entry was maker order
        maker_exit: Exit was maker order

    Returns:
        (total_fees, total_fees_pct_of_notional)
    """
    notional = entry_price * qty

    entry_fee = calculate_trading_fee(notional, maker_entry)
    exit_fee = calculate_trading_fee(notional, maker_exit)

    total_fees = entry_fee + exit_fee
    total_fees_pct = (total_fees / notional) * Decimal("100")

    return (total_fees, total_fees_pct)


def minimum_profitable_move(
    is_maker_entry: bool = True,
    is_maker_exit: bool = True
) -> Decimal:
    """
    Calculate minimum price move (%) needed to break even after fees.

    Args:
        is_maker_entry: Entry as maker
        is_maker_exit: Exit as maker

    Returns:
        Minimum profitable move as percentage
    """
    entry_fee_pct = settings.maker_fee_pct if is_maker_entry else settings.taker_fee_pct
    exit_fee_pct = settings.maker_fee_pct if is_maker_exit else settings.taker_fee_pct

    # Total fees as % of notional
    total_fee_pct = entry_fee_pct + exit_fee_pct

    # Need to overcome fees plus make them back on exit
    # Simplified: need to gain > fees / (1 - exit_fee)
    min_move_pct = total_fee_pct / (Decimal("1") - exit_fee_pct / Decimal("100"))

    return min_move_pct
