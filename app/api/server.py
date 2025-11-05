"""
FastAPI server for controlling the trading system.
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime
import pandas as pd
from app.services.paper_trader import PaperTrader
from app.services.live_trader import LiveTrader
from app.services.backtester import Backtester, BacktestConfig
from app.core.config import settings
from app.db.database import init_db, get_db
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Volatility Harvester API",
    description="Control API for BTC Volatility Harvesting Trading Engine",
    version="1.0.0"
)

# Global trader instances
paper_trader: Optional[PaperTrader] = None
live_trader: Optional[LiveTrader] = None


# Request models
class StartTradingRequest(BaseModel):
    mode: str  # "paper" or "live"
    initial_capital: Optional[float] = 10000.0


class BacktestRequest(BaseModel):
    start_date: str  # ISO format
    end_date: Optional[str] = None
    initial_capital: float = 10000.0
    buy_threshold_pct: float = 5.0
    sell_threshold_pct: float = 5.0
    adaptive_thresholds: bool = True


# Startup
@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info("Starting Volatility Harvester API...")
    init_db()
    logger.info("API ready")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down...")
    global paper_trader, live_trader

    if paper_trader and paper_trader.running:
        await paper_trader.stop()

    if live_trader and live_trader.running:
        await live_trader.stop()


# Health check
@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "mode": settings.mode
    }


# Status
@app.get("/status")
async def get_status():
    """Get current trading status."""
    global paper_trader, live_trader

    trader = paper_trader if settings.mode == "paper" else live_trader

    if trader and trader.running:
        return trader.get_status()
    else:
        return {
            "running": False,
            "mode": settings.mode
        }


# Start trading
@app.post("/start")
async def start_trading(request: StartTradingRequest):
    """Start trading in paper or live mode."""
    global paper_trader, live_trader

    if request.mode not in ["paper", "live"]:
        raise HTTPException(status_code=400, detail="Mode must be 'paper' or 'live'")

    # Check if already running
    if request.mode == "paper":
        if paper_trader and paper_trader.running:
            raise HTTPException(status_code=400, detail="Paper trader already running")

        paper_trader = PaperTrader(Decimal(str(request.initial_capital)))
        await paper_trader.start()

        return {
            "status": "started",
            "mode": "paper",
            "initial_capital": request.initial_capital
        }

    elif request.mode == "live":
        if live_trader and live_trader.running:
            raise HTTPException(status_code=400, detail="Live trader already running")

        # Extra confirmation for live trading
        logger.warning("Starting LIVE trading with REAL MONEY")

        live_trader = LiveTrader()
        await live_trader.start()

        return {
            "status": "started",
            "mode": "live",
            "message": "LIVE TRADING ACTIVE - REAL MONEY AT RISK"
        }


# Stop trading
@app.post("/stop")
async def stop_trading():
    """Stop trading."""
    global paper_trader, live_trader

    if paper_trader and paper_trader.running:
        await paper_trader.stop()
        return {"status": "stopped", "mode": "paper"}

    elif live_trader and live_trader.running:
        await live_trader.stop()
        return {"status": "stopped", "mode": "live"}

    else:
        raise HTTPException(status_code=400, detail="No trader running")


# Emergency flatten
@app.post("/emergency-flatten")
async def emergency_flatten():
    """Emergency position flatten (live mode only)."""
    global live_trader

    if not live_trader or not live_trader.running:
        raise HTTPException(status_code=400, detail="Live trader not running")

    await live_trader.emergency_flatten()

    return {
        "status": "flattened",
        "message": "Emergency flatten executed"
    }


# Backtest
@app.post("/backtest")
async def run_backtest(request: BacktestRequest, db: Session = Depends(get_db)):
    """Run backtest."""
    try:
        from app.data.candles_repo import CandlesRepository

        # Load candles from database
        candles_repo = CandlesRepository(db)
        start_date = datetime.fromisoformat(request.start_date)
        end_date = datetime.fromisoformat(request.end_date) if request.end_date else None

        candles = candles_repo.get_candles(
            symbol=settings.symbol,
            timeframe="1m",
            start=start_date,
            end=end_date
        )

        if not candles:
            raise HTTPException(status_code=404, detail="No candles found for date range")

        candles_df = candles_repo.candles_to_dataframe(candles)

        # Create backtest config
        config = BacktestConfig(
            initial_capital=Decimal(str(request.initial_capital)),
            buy_threshold_pct=Decimal(str(request.buy_threshold_pct)),
            sell_threshold_pct=Decimal(str(request.sell_threshold_pct)),
            adaptive_thresholds=request.adaptive_thresholds
        )

        # Run backtest
        backtester = Backtester(config)
        result = backtester.run(candles_df, settings.symbol)

        # Return results
        return {
            "initial_capital": result.initial_capital,
            "final_capital": result.final_capital,
            "total_pnl": result.total_pnl,
            "total_pnl_pct": result.total_pnl_pct,
            "total_trades": result.total_trades,
            "win_rate": result.win_rate,
            "max_drawdown_pct": result.max_drawdown_pct,
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "cagr": result.cagr,
            "total_fees_paid": result.total_fees_paid,
            "config": result.config,
            "trades": result.trades[:100]  # Limit to first 100 trades in response
        }

    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Get configuration
@app.get("/config")
async def get_config():
    """Get current configuration."""
    return {
        "exchange": settings.exchange,
        "symbol": settings.symbol,
        "mode": settings.mode,
        "buy_threshold_pct": float(settings.buy_threshold_pct),
        "sell_threshold_pct": float(settings.sell_threshold_pct),
        "adaptive_thresholds": settings.adaptive_thresholds,
        "max_drawdown_pct": float(settings.max_drawdown_pct),
        "max_consecutive_losses": settings.max_consecutive_losses,
        "maker_first": settings.maker_first,
        "reserve_pct": float(settings.reserve_pct)
    }


# Get metrics (Prometheus format)
@app.get("/metrics")
async def get_metrics():
    """Get metrics in Prometheus format."""
    global paper_trader, live_trader

    trader = paper_trader if settings.mode == "paper" else live_trader

    if not trader or not trader.running:
        return "# No trader running\n"

    status = trader.get_status()

    metrics = []
    metrics.append(f"# HELP volharvester_equity_usd Current total equity in USD")
    metrics.append(f"# TYPE volharvester_equity_usd gauge")
    metrics.append(f"volharvester_equity_usd {status['equity']}")

    metrics.append(f"# HELP volharvester_realized_pnl_usd Realized PnL in USD")
    metrics.append(f"# TYPE volharvester_realized_pnl_usd gauge")
    metrics.append(f"volharvester_realized_pnl_usd {status['realized_pnl']}")

    metrics.append(f"# HELP volharvester_unrealized_pnl_usd Unrealized PnL in USD")
    metrics.append(f"# TYPE volharvester_unrealized_pnl_usd gauge")
    metrics.append(f"volharvester_unrealized_pnl_usd {status['unrealized_pnl']}")

    metrics.append(f"# HELP volharvester_total_trades Total number of trades")
    metrics.append(f"# TYPE volharvester_total_trades counter")
    metrics.append(f"volharvester_total_trades {status['total_trades']}")

    metrics.append(f"# HELP volharvester_win_rate Win rate percentage")
    metrics.append(f"# TYPE volharvester_win_rate gauge")
    metrics.append(f"volharvester_win_rate {status['win_rate']}")

    metrics.append(f"# HELP volharvester_drawdown_pct Current drawdown percentage")
    metrics.append(f"# TYPE volharvester_drawdown_pct gauge")
    metrics.append(f"volharvester_drawdown_pct {status['drawdown_pct']}")

    metrics.append(f"# HELP volharvester_paused Whether trading is paused")
    metrics.append(f"# TYPE volharvester_paused gauge")
    metrics.append(f"volharvester_paused {1 if status['paused'] else 0}")

    return "\n".join(metrics)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
