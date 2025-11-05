"""
Configuration management using pydantic settings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Literal, Optional
from decimal import Decimal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Exchange Configuration
    exchange: Literal["coinbase", "binance"] = "coinbase"
    symbol: str = "BTC-USD"
    mode: Literal["backtest", "paper", "live"] = "backtest"

    # Exchange API Keys
    coinbase_api_key: str = ""
    coinbase_api_secret: str = ""
    binance_api_key: str = ""
    binance_api_secret: str = ""

    # Strategy Parameters
    buy_threshold_pct: Decimal = Field(default=Decimal("5.0"), ge=1.0, le=20.0)
    sell_threshold_pct: Decimal = Field(default=Decimal("5.0"), ge=1.0, le=20.0)
    min_swing_pct: Decimal = Field(default=Decimal("2.0"), ge=0.5, le=10.0)
    max_swing_pct: Decimal = Field(default=Decimal("8.0"), ge=3.0, le=20.0)
    adaptive_thresholds: bool = True
    tiered_entry: bool = False
    num_tranches: int = Field(default=5, ge=2, le=10)
    reserve_pct: Decimal = Field(default=Decimal("8.0"), ge=0.0, le=50.0)

    # Risk Management
    max_drawdown_pct: Decimal = Field(default=Decimal("20.0"), ge=5.0, le=50.0)
    max_consecutive_losses: int = Field(default=5, ge=1, le=20)
    daily_loss_limit_pct: Decimal = Field(default=Decimal("10.0"), ge=1.0, le=50.0)
    min_activity_pct: Decimal = Field(default=Decimal("2.0"), ge=0.0, le=10.0)
    max_activity_pct: Decimal = Field(default=Decimal("10.0"), ge=5.0, le=50.0)
    max_spread_bps: int = Field(default=10, ge=1, le=100)
    max_ws_stale_seconds: int = Field(default=5, ge=1, le=60)

    # Execution
    maker_first: bool = True
    taker_slippage_bps: int = Field(default=10, ge=0, le=100)
    min_notional_usd: Decimal = Field(default=Decimal("10.0"), ge=1.0)
    order_timeout_seconds: int = Field(default=30, ge=5, le=300)

    # Fees
    maker_fee_pct: Decimal = Field(default=Decimal("0.10"), ge=0.0, le=1.0)
    taker_fee_pct: Decimal = Field(default=Decimal("0.30"), ge=0.0, le=1.0)

    # Volatility Calculation
    atr_period: int = Field(default=14, ge=5, le=50)
    atr_timeframe_short: str = "1m"
    atr_timeframe_long: str = "15m"

    # Trend Filter
    use_trend_filter: bool = False
    ma_short: int = Field(default=50, ge=10, le=100)
    ma_long: int = Field(default=200, ge=100, le=500)

    # Database
    database_url: str = "postgresql://volharvester:volharvester@localhost:5432/volharvester"

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "text"] = "json"

    # Metrics
    metrics_port: int = Field(default=9090, ge=1024, le=65535)
    enable_metrics: bool = True

    # Scheduler
    backtest_cron: str = "0 2 * * *"
    report_email: Optional[str] = None
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Application
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1024, le=65535)

    @validator("sell_threshold_pct")
    def validate_sell_threshold(cls, v, values):
        """Ensure sell threshold is reasonable relative to buy threshold."""
        if "buy_threshold_pct" in values and v < values["buy_threshold_pct"] * Decimal("0.5"):
            raise ValueError("Sell threshold should be at least 50% of buy threshold")
        return v

    @validator("max_swing_pct")
    def validate_max_swing(cls, v, values):
        """Ensure max swing is greater than min swing."""
        if "min_swing_pct" in values and v <= values["min_swing_pct"]:
            raise ValueError("Max swing must be greater than min swing")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
