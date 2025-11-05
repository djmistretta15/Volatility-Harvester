"""
Slippage estimation for backtesting.
"""
from decimal import Decimal
from app.core.config import settings


def estimate_slippage(
    price: Decimal,
    qty: Decimal,
    atr_pct: Decimal,
    is_maker: bool = True
) -> Decimal:
    """
    Estimate slippage for an order.

    For maker orders: minimal slippage (already in the book)
    For taker orders: slippage scales with volatility

    Args:
        price: Order price
        qty: Order quantity
        atr_pct: Current ATR as percentage
        is_maker: Whether this is a maker order

    Returns:
        Estimated slippage in USD
    """
    if is_maker:
        # Maker orders get price improvement or no slippage
        return Decimal("0")

    # Taker slippage: base + volatility component
    base_slippage_bps = settings.taker_slippage_bps
    volatility_slippage_bps = (atr_pct / Decimal("5")) * Decimal("5")  # Scale with volatility

    total_slippage_bps = base_slippage_bps + volatility_slippage_bps

    slippage_pct = total_slippage_bps / Decimal("10000")
    slippage_usd = price * qty * slippage_pct

    return slippage_usd


def adjust_fill_price_for_slippage(
    price: Decimal,
    side: str,
    atr_pct: Decimal,
    is_maker: bool = True
) -> Decimal:
    """
    Adjust fill price to account for slippage.

    Args:
        price: Original price
        side: "buy" or "sell"
        atr_pct: Current ATR percentage
        is_maker: Whether this is a maker order

    Returns:
        Adjusted price
    """
    if is_maker:
        return price  # No adjustment for maker

    base_slippage_bps = settings.taker_slippage_bps
    volatility_slippage_bps = (atr_pct / Decimal("5")) * Decimal("5")
    total_slippage_bps = base_slippage_bps + volatility_slippage_bps
    slippage_pct = total_slippage_bps / Decimal("10000")

    if side == "buy":
        # Pay more when buying
        return price * (Decimal("1") + slippage_pct)
    else:
        # Receive less when selling
        return price * (Decimal("1") - slippage_pct)
