# 🚀 Quick Start Guide - Run It Now!

Get the Volatility Harvester up and running in 5 steps:

## Step 1: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your exchange API keys
nano .env
```

**Minimum required changes:**
```bash
# For paper trading (no keys needed)
MODE=paper

# For live trading (REQUIRED)
COINBASE_API_KEY=your_api_key_here
COINBASE_API_SECRET=your_api_secret_here
```

## Step 2: Start Services

```bash
# Start all services (Postgres, API, Prometheus, Grafana)
make up

# Wait ~30 seconds for services to initialize
# You should see: "Services started!"
```

**Services:**
- API: http://localhost:8000
- Metrics: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9091

## Step 3: Run Backtest

```bash
# Run a backtest to verify the system works
make backtest
```

**Note:** You'll need historical data first. To get started with test data:

```bash
# Access the app container
make shell

# Run Python to generate test data (optional for first run)
python -c "
from app.adapters.fake_exchange import FakeExchange
from app.data.ingest import DataIngester
import asyncio
from datetime import datetime, timedelta

async def generate_data():
    exchange = FakeExchange(initial_price=50000)
    await exchange.connect()
    ingester = DataIngester(exchange, 'BTC-USD')

    # Generate 30 days of 1-minute candles
    start = datetime.utcnow() - timedelta(days=30)
    await ingester.backfill_candles('1m', start)

asyncio.run(generate_data())
"
```

Or use the API:

```bash
curl -X POST http://localhost:8000/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2023-01-01T00:00:00",
    "end_date": "2023-12-31T23:59:59",
    "initial_capital": 10000,
    "buy_threshold_pct": 5.0,
    "sell_threshold_pct": 5.0,
    "adaptive_thresholds": true
  }'
```

## Step 4: Paper Trade

```bash
# Start paper trading with $10,000 simulated capital
make paper

# Check status
make status

# Watch logs in real-time
make logs
```

**What you'll see:**
- Real-time price simulation
- Buy/sell signals
- Position tracking
- PnL updates

**Let it run for at least 1 hour to see some trades.**

To stop:
```bash
make paper-stop
```

## Step 5: Go Live (⚠️ REAL MONEY)

**ONLY after successful paper trading!**

```bash
# ⚠️ WARNING: This trades with REAL MONEY
# Make sure you:
# 1. Tested thoroughly in paper mode
# 2. Configured exchange API keys
# 3. Set appropriate risk limits in .env
# 4. Started with small capital

make live

# Monitor continuously
make status
make logs

# Emergency stop (keeps position)
make live-stop

# Emergency flatten (sells everything immediately)
make live-flatten
```

## Monitoring

### Check Status

```bash
# Via make
make status

# Via curl
curl http://localhost:8000/status
```

### View Logs

```bash
# Real-time logs
make logs

# Last 100 lines
docker-compose logs --tail=100 app
```

### Metrics & Dashboards

1. **Prometheus Metrics**: http://localhost:9090/metrics
2. **Grafana Dashboard**: http://localhost:3000
   - Login: admin/admin
   - Add datasource: http://prometheus:9090
   - Create dashboard with metrics from `/metrics` endpoint

## Configuration

### Quick Tweaks

Edit `.env` and restart:

```bash
# More conservative (wider thresholds, fewer trades)
BUY_THRESHOLD_PCT=7.0
SELL_THRESHOLD_PCT=7.0

# More aggressive (tighter thresholds, more trades)
BUY_THRESHOLD_PCT=3.0
SELL_THRESHOLD_PCT=3.0

# Restart to apply
make restart
```

### Key Parameters

| Parameter | Default | Conservative | Aggressive |
|-----------|---------|--------------|------------|
| BUY_THRESHOLD_PCT | 5.0 | 7.0 | 3.0 |
| SELL_THRESHOLD_PCT | 5.0 | 7.0 | 3.0 |
| MAX_DRAWDOWN_PCT | 20.0 | 15.0 | 25.0 |
| RESERVE_PCT | 8.0 | 15.0 | 5.0 |

## Troubleshooting

### Services won't start

```bash
# Check if ports are in use
lsof -i :5432  # Postgres
lsof -i :8000  # API

# View error logs
docker-compose logs
```

### Database errors

```bash
# Reset database
make down
docker volume rm volatility-harvester_postgres_data
make up
```

### API not responding

```bash
# Check health
curl http://localhost:8000/healthz

# Restart API
make restart
```

### Paper trading not generating trades

**Possible reasons:**
1. Thresholds too wide for current volatility
2. Already in position (check status)
3. Circuit breaker triggered (check logs)

**Solutions:**
- Wait longer (may need several hours for 5% move)
- Reduce thresholds temporarily
- Check status: `make status`

## Common Commands

```bash
# Development
make install        # Install dependencies
make dev           # Run in development mode
make test          # Run tests

# Operations
make up            # Start all services
make down          # Stop all services
make restart       # Restart services
make logs          # View logs
make status        # Check trading status

# Trading
make backtest      # Run backtest
make paper         # Start paper trading
make paper-stop    # Stop paper trading
make live          # Start live trading (⚠️ REAL MONEY)
make live-stop     # Stop live trading
make live-flatten  # Emergency exit all positions

# Database
make migrate       # Run migrations
make db-shell      # PostgreSQL shell

# Cleanup
make clean         # Remove containers and volumes
```

## What's Next?

After running through these 5 steps:

1. ✅ **Read the docs**:
   - [STRATEGY.md](docs/STRATEGY.md) - Understand the strategy
   - [RISK.md](docs/RISK.md) - Learn risk management
   - [BACKTESTING.md](docs/BACKTESTING.md) - Master backtesting

2. ✅ **Run backtests**: Test different parameters for your style

3. ✅ **Paper trade**: Let it run for at least 1 week

4. ✅ **Start small**: Begin live with minimum capital ($100-$500)

5. ✅ **Monitor & adjust**: Track performance, tune parameters

## Need Help?

- Check logs: `make logs`
- Review status: `make status`
- Read documentation: `docs/`
- Check configuration: `curl http://localhost:8000/config`

---

**Happy trading! Remember: Start small, monitor closely, and never risk more than you can afford to lose.**

🎯 **First time?** Start with paper trading and let it run for a few hours to see signals and trades in action.
