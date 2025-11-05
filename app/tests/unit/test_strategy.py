"""
Unit tests for strategy module.
"""
import pytest
from decimal import Decimal
from datetime import datetime
import pandas as pd
import numpy as np
from app.core.strategy import VolatilityHarvester
from app.core.models import StrategyStateData, MarketData
from app.core.enums import StrategyState


class TestVolatilityHarvester:
    """Test VolatilityHarvester strategy."""

    def setup_method(self):
        """Setup for each test."""
        self.strategy = VolatilityHarvester(
            buy_threshold_pct=Decimal("5.0"),
            sell_threshold_pct=Decimal("5.0"),
            adaptive=False
        )

    def test_calculate_atr_pct(self):
        """Test ATR calculation."""
        # Create sample candles
        candles = pd.DataFrame({
            'high': [101, 102, 103, 102, 101, 100, 99, 100, 101, 102,
                    103, 104, 105, 104, 103, 102, 101, 100, 99, 100],
            'low': [99, 100, 101, 100, 99, 98, 97, 98, 99, 100,
                   101, 102, 103, 102, 101, 100, 99, 98, 97, 98],
            'close': [100, 101, 102, 101, 100, 99, 98, 99, 100, 101,
                     102, 103, 104, 103, 102, 101, 100, 99, 98, 99]
        })

        atr_pct = self.strategy.calculate_atr_pct(candles, period=14)

        assert isinstance(atr_pct, Decimal)
        assert atr_pct > 0
        assert atr_pct < 100  # Sanity check

    def test_generate_buy_signal_on_dip(self):
        """Test buy signal generation on price dip."""
        state = StrategyStateData()
        state.state = StrategyState.FLAT
        state.last_peak = Decimal("50000")

        # Price drops 5% from peak
        market_data = MarketData(
            symbol="BTC-USD",
            timestamp=datetime.utcnow(),
            bid=Decimal("47400"),
            ask=Decimal("47600"),
            last=Decimal("47500")
        )

        signal = self.strategy.generate_signal(state, market_data)

        assert signal.signal_type == "buy"
        assert "5.0" in signal.reason or "5%" in signal.reason

    def test_generate_sell_signal_on_rebound(self):
        """Test sell signal generation on price rebound."""
        state = StrategyStateData()
        state.state = StrategyState.LONG
        state.last_buy_price = Decimal("47500")

        # Price rises 5% from entry
        market_data = MarketData(
            symbol="BTC-USD",
            timestamp=datetime.utcnow(),
            bid=Decimal("49800"),
            ask=Decimal("50000"),
            last=Decimal("49875")
        )

        signal = self.strategy.generate_signal(state, market_data)

        assert signal.signal_type == "sell"
        assert "5.0" in signal.reason or "5%" in signal.reason

    def test_no_signal_when_threshold_not_met(self):
        """Test that no signal is generated when threshold not met."""
        state = StrategyStateData()
        state.state = StrategyState.FLAT
        state.last_peak = Decimal("50000")

        # Price drops only 3% (threshold is 5%)
        market_data = MarketData(
            symbol="BTC-USD",
            timestamp=datetime.utcnow(),
            bid=Decimal("48400"),
            ask=Decimal("48600"),
            last=Decimal("48500")
        )

        signal = self.strategy.generate_signal(state, market_data)

        assert signal.signal_type == "hold"

    def test_calculate_position_size(self):
        """Test position size calculation."""
        available_capital = Decimal("10000")
        current_price = Decimal("50000")
        reserve_pct = Decimal("10")

        qty = self.strategy.calculate_position_size(
            available_capital, current_price, reserve_pct
        )

        # Should deploy 90% of capital
        expected_qty = (available_capital * Decimal("0.9")) / current_price
        assert qty == expected_qty

    def test_update_state_after_buy(self):
        """Test state update after buy."""
        state = StrategyStateData()
        state.state = StrategyState.FLAT

        self.strategy.update_state_after_buy(
            state,
            fill_price=Decimal("47500"),
            qty=Decimal("0.1"),
            timestamp=datetime.utcnow()
        )

        assert state.state == StrategyState.LONG
        assert state.last_buy_price == Decimal("47500")
        assert state.current_position_qty == Decimal("0.1")

    def test_update_state_after_sell(self):
        """Test state update after sell."""
        state = StrategyStateData()
        state.state = StrategyState.LONG
        state.last_buy_price = Decimal("47500")

        self.strategy.update_state_after_sell(
            state,
            fill_price=Decimal("50000"),
            realized_pnl=Decimal("250"),
            timestamp=datetime.utcnow()
        )

        assert state.state == StrategyState.FLAT
        assert state.last_sell_price == Decimal("50000")
        assert state.current_position_qty == Decimal("0")
        assert state.realized_pnl == Decimal("250")

    def test_adapt_thresholds_low_volatility(self):
        """Test threshold adaptation for low volatility."""
        adaptive_strategy = VolatilityHarvester(
            buy_threshold_pct=Decimal("5.0"),
            sell_threshold_pct=Decimal("5.0"),
            adaptive=True,
            min_swing_pct=Decimal("2.0"),
            max_swing_pct=Decimal("8.0")
        )

        # Low volatility (1.5%)
        buy_thresh, sell_thresh = adaptive_strategy.adapt_thresholds(Decimal("1.5"))

        # Should use minimum
        assert buy_thresh == Decimal("2.0")
        assert sell_thresh == Decimal("2.0")

    def test_adapt_thresholds_high_volatility(self):
        """Test threshold adaptation for high volatility."""
        adaptive_strategy = VolatilityHarvester(
            buy_threshold_pct=Decimal("5.0"),
            sell_threshold_pct=Decimal("5.0"),
            adaptive=True,
            min_swing_pct=Decimal("2.0"),
            max_swing_pct=Decimal("8.0")
        )

        # High volatility (7.0%)
        buy_thresh, sell_thresh = adaptive_strategy.adapt_thresholds(Decimal("7.0"))

        # Should use maximum
        assert buy_thresh == Decimal("8.0")
        assert sell_thresh == Decimal("8.0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
