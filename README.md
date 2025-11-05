# Volatility Harvester

A production-grade BTC volatility harvesting trading engine with backtesting, paper trading, and live trading capabilities.

## Overview

The Volatility Harvester implements a systematic trading strategy that profits from Bitcoin's natural price oscillations by buying on dips and selling on rebounds. The system features:

- **Beautiful Dashboard** - Real-time React UI with live charts and metrics
- **Fee-aware execution** with maker/taker optimization
- **Full compounding** through all-in/all-out position management
- **Adaptive thresholds** based on market volatility (ATR)
- **Comprehensive risk management** with multiple circuit breakers
- **Multi-mode operation**: Backtest → Paper Trade → Live Trade pipeline

## 🎨 Dashboard

The system includes a **stunning, production-grade web dashboard** built with React + TypeScript:

- **Real-time Metrics** - Equity, P&L, win rate, drawdown updating every 2 seconds
- **Interactive Charts** - Beautiful equity curve with trend predictions
- **Live Trade Feed** - See every trade as it executes with P&L
- **Risk Monitoring** - Circuit breaker status and health indicators
- **One-Click Controls** - Start/stop paper or live trading from the UI
- **Responsive Design** - Works perfectly on desktop, tablet, and mobile

Access at **http://localhost:3000** after running `make up`

![Dashboard Preview](docs/dashboard-preview.png) *(Coming soon)*

## Quick Start

### 1. Setup

```bash
# Clone repository
git clone <repo-url>
cd Volatility-Harvester

# Copy environment template
cp .env.example .env

# Edit .env with your exchange API keys
nano .env
```

### 2. Start Services

```bash
# Start all services (Dashboard, API, Postgres, Prometheus, Grafana)
make up

# Wait for services to be ready (~30 seconds)
# 🎨 Dashboard: http://localhost:3000
# 🔌 API: http://localhost:8000
```

### 3. Run Backtest

```bash
# Run backtest (requires historical data)
make backtest

# Or via API:
curl -X POST http://localhost:8000/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2023-01-01T00:00:00",
    "end_date": "2023-12-31T23:59:59",
    "initial_capital": 10000,
    "buy_threshold_pct": 5.0,
    "sell_threshold_pct": 5.0
  }'
```

### 4. Paper Trade

```bash
# Start paper trading with simulated exchange
make paper

# Check status
make status

# Stop paper trading
make paper-stop
```

### 5. Live Trade (⚠️ REAL MONEY)

```bash
# ⚠️ WARNING: Live trading uses real money
# Ensure you have:
# 1. Tested thoroughly in paper mode
# 2. Configured risk limits appropriately
# 3. Set up API keys with appropriate permissions

make live

# Monitor status
make status

# Stop live trading
make live-stop

# Emergency flatten (sell all immediately)
make live-flatten
```

## Architecture

```
app/
├── adapters/         # Exchange adapters (Coinbase, Binance, Fake)
├── api/             # FastAPI server
├── core/            # Core trading logic
│   ├── config.py    # Configuration management
│   ├── strategy.py  # Volatility harvesting strategy
│   ├── risk.py      # Risk management & circuit breakers
│   ├── execution.py # Order execution engine
│   ├── portfolio.py # Portfolio tracking
│   └── models.py    # Data models
├── data/            # Data ingestion & storage
├── db/              # Database & migrations
└── services/        # Trading services
    ├── backtester.py   # Vectorized backtesting
    ├── paper_trader.py # Paper trading
    └── live_trader.py  # Live trading
```

## Strategy

The Volatility Harvester uses swing thresholds to enter and exit positions:

- **Buy Trigger**: Price drops X% from recent peak (default 5%)
- **Sell Trigger**: Price rises Y% from entry (default 5%)
- **Adaptive Mode**: Thresholds adjust based on ATR
  - Low volatility (< 2.5%): Reduce thresholds
  - High volatility (> 6%): Increase thresholds

See [STRATEGY.md](docs/STRATEGY.md) for detailed strategy documentation.

## Risk Management

Multiple circuit breakers protect capital:

1. **Max Drawdown** (default 20%): Pause trading if drawdown exceeds limit
2. **Consecutive Losses** (default 5): Pause after multiple losing trades
3. **Daily Loss Limit** (default 10%): Stop trading if daily losses exceed threshold
4. **Volatility Bounds**: Pause if ATR too low (choppy) or too high (chaos)
5. **Spread Guard**: Block trades if spread too wide
6. **Latency Guard**: Pause if exchange data is stale

See [RISK.md](docs/RISK.md) for complete risk documentation.

## Configuration

Key parameters in `.env`:

```bash
# Strategy
BUY_THRESHOLD_PCT=5.0       # Buy dip threshold
SELL_THRESHOLD_PCT=5.0      # Sell rebound threshold
ADAPTIVE_THRESHOLDS=true    # Auto-adjust based on volatility
RESERVE_PCT=8.0             # Keep 8% cash in reserve

# Risk
MAX_DRAWDOWN_PCT=20.0       # Max drawdown before pause
MAX_CONSECUTIVE_LOSSES=5    # Max consecutive losses
MAX_SPREAD_BPS=10           # Max spread in basis points

# Execution
MAKER_FIRST=true            # Try limit orders first
MAKER_FEE_PCT=0.10          # 0.1% maker fee
TAKER_FEE_PCT=0.30          # 0.3% taker fee
```

## API Endpoints

- `GET /healthz` - Health check
- `GET /status` - Current trading status
- `GET /config` - Current configuration
- `GET /metrics` - Prometheus metrics
- `POST /start` - Start trading (paper or live)
- `POST /stop` - Stop trading
- `POST /backtest` - Run backtest
- `POST /emergency-flatten` - Emergency position exit

## Monitoring

### Prometheus Metrics

Available at `http://localhost:9090/metrics`:

- `volharvester_equity_usd` - Current total equity
- `volharvester_realized_pnl_usd` - Realized PnL
- `volharvester_unrealized_pnl_usd` - Unrealized PnL
- `volharvester_total_trades` - Total trade count
- `volharvester_win_rate` - Win rate percentage
- `volharvester_drawdown_pct` - Current drawdown
- `volharvester_paused` - Circuit breaker status

### Grafana Dashboards

Access Grafana at `http://localhost:3000` (admin/admin):

1. Add Prometheus datasource: `http://prometheus:9090`
2. Import dashboards from `grafana/` directory
3. Monitor equity, PnL, trades, and risk metrics

## Development

```bash
# Install dependencies
make install

# Run tests
make test

# Run in development mode (auto-reload)
make dev

# View logs
make logs

# Access container shell
make shell

# Database shell
make db-shell

# Clean up
make clean
```

## Backtesting

See [BACKTESTING.md](docs/BACKTESTING.md) for:

- Parameter sweeps
- Walk-forward analysis
- Performance metrics
- Result interpretation

## Safety & Best Practices

### Before Live Trading

1. ✅ Run extensive backtests on historical data
2. ✅ Paper trade for at least 1 week
3. ✅ Verify all circuit breakers trigger correctly
4. ✅ Test emergency flatten procedure
5. ✅ Start with small capital
6. ✅ Monitor closely for first 24 hours

### During Live Trading

- Monitor equity and PnL continuously
- Check for circuit breaker triggers
- Verify order fills and fees
- Watch for API rate limits
- Keep emergency flatten ready

### Never

- ❌ Trade more than you can afford to lose
- ❌ Disable circuit breakers
- ❌ Use production API keys in development
- ❌ Deploy without testing
- ❌ Leave unmonitored

## Support & Contributing

For issues, questions, or contributions:

1. Check existing documentation
2. Review logs: `make logs`
3. Open an issue with details
4. Submit pull requests with tests

## License

MIT License - See LICENSE file

## Disclaimer

**This software is for educational purposes only. Trading cryptocurrencies involves substantial risk of loss. The authors are not responsible for any financial losses incurred through the use of this software. Always test thoroughly and trade responsibly.**

---

Built with ❤️ for systematic traders