# Risk Management Documentation

## Overview

The Volatility Harvester implements multiple layers of risk management to protect capital and prevent catastrophic losses.

## Circuit Breakers

### 1. Maximum Drawdown (Default: 20%)

**Trigger:** When equity falls more than X% from peak equity

**Action:** Pause all trading

**Rationale:**
- Protects against sustained losing streaks
- Forces re-evaluation of market conditions
- Prevents "death spiral" scenarios

**Configuration:**
```bash
MAX_DRAWDOWN_PCT=20.0
```

**Example:**
- Peak equity: $10,000
- Current equity: $7,900
- Drawdown: 21% → Circuit breaker triggers
- Trading paused until manual reset

**When it triggers:**
- Multiple consecutive losses
- Adverse market regime
- Strategy parameters misaligned with market

**Recovery:**
- Analyze what caused the drawdown
- Adjust parameters if needed
- Reset manually when ready

### 2. Consecutive Losses (Default: 5)

**Trigger:** After N consecutive losing trades

**Action:** Pause trading for cooldown

**Rationale:**
- Indicates strategy is out of sync with market
- Prevents compounding losses
- Forces manual review

**Configuration:**
```bash
MAX_CONSECUTIVE_LOSSES=5
```

**Example:**
- Trade 1: -$200
- Trade 2: -$150
- Trade 3: -$100
- Trade 4: -$180
- Trade 5: -$220
- → Circuit breaker triggers after trade 5

**When it triggers:**
- Trending market (strategy expects mean reversion)
- High volatility causing whipsaws
- Incorrect parameters

**Recovery:**
- Wait for market to settle
- Consider adjusting thresholds
- Re-enable manually

### 3. Daily Loss Limit (Default: 10%)

**Trigger:** When daily losses exceed X% of equity

**Action:** Pause trading until next day (UTC reset)

**Rationale:**
- Limits damage from bad trading days
- Enforces discipline
- Prevents emotional decision-making

**Configuration:**
```bash
DAILY_LOSS_LIMIT_PCT=10.0
```

**Example:**
- Starting equity: $10,000
- Losses today: -$1,050
- Daily loss: 10.5% → Pause trading
- Resumes automatically at UTC midnight

**When it triggers:**
- Volatile trading day
- Multiple failed trades
- Extreme market movements

### 4. Volatility Bounds

**Low Volatility (ATR < 2.0%)**

**Trigger:** Market too choppy/range-bound

**Action:** Pause trading or reduce position size

**Rationale:**
- Small moves don't cover fees
- Increased risk of whipsaws
- Better to wait for clearer conditions

**High Volatility (ATR > 10.0%)**

**Trigger:** Market too volatile/chaotic

**Action:** Pause trading

**Rationale:**
- Extreme volatility = higher slippage
- Unpredictable price action
- Risk of flash crashes

**Configuration:**
```bash
MIN_ACTIVITY_PCT=2.0
MAX_ACTIVITY_PCT=10.0
```

### 5. Spread Guard (Default: 10 bps)

**Trigger:** When bid-ask spread exceeds threshold

**Action:** Block trade execution

**Rationale:**
- Wide spreads = poor liquidity
- High implicit transaction costs
- Market stress indicator

**Configuration:**
```bash
MAX_SPREAD_BPS=10
```

**Example:**
- BTC price: $50,000
- Bid: $49,975
- Ask: $50,025
- Spread: $50 / $50,000 = 10 bps → Allow
- If spread: $100 = 20 bps → Block trade

### 6. Data Staleness Guard (Default: 5 seconds)

**Trigger:** When exchange data hasn't updated recently

**Action:** Pause trading immediately

**Rationale:**
- Trading on stale data = blind trading
- Indicates connection issues
- Prevents orders at outdated prices

**Configuration:**
```bash
MAX_WS_STALE_SECONDS=5
```

**Example:**
- Last WebSocket update: 6 seconds ago
- → Pause trading
- → Try to reconnect
- → Resume when fresh data available

## Position Risk Management

### Reserve Cash

Always keep a small reserve (5-10%):

```bash
RESERVE_PCT=8.0
```

**Reasons:**
- Cover rounding errors
- Handle fee variations
- Emergency liquidity
- Account minimums

### Minimum Notional

Enforce minimum trade size:

```bash
MIN_NOTIONAL_USD=10.0
```

**Prevents:**
- Sub-economic trades (fees > profit)
- Exchange rejection (below minimum)
- Execution issues

### Order Validation

Before every order:
1. Check available balance
2. Validate against min notional
3. Round to exchange lot size
4. Verify within risk limits

## Emergency Procedures

### Emergency Flatten

Immediately sell all positions at market:

```bash
make live-flatten
```

**Use when:**
- Critical bug detected
- Exchange issues
- Regulatory concerns
- Personal emergency

**Warning:** Executes as MARKET order, accepts slippage

### Manual Pause/Resume

Pause trading without flattening:

```bash
curl -X POST http://localhost:8000/stop
```

**Use when:**
- Suspicious activity
- Want to review logs
- Planned maintenance
- Risk limit reached

### Circuit Breaker Reset

After circuit breaker triggers:

1. **Review logs**: Understand what triggered it
2. **Analyze trades**: Look for patterns
3. **Check market**: Ensure conditions normalized
4. **Adjust parameters**: If needed
5. **Test in paper mode**: Verify fix
6. **Resume carefully**: Start with small size

## Risk Metrics Monitoring

### Real-Time Metrics

Monitor continuously:

- **Current PnL**: Realized + Unrealized
- **Drawdown**: Current vs peak
- **Win rate**: Rolling 10/20/50 trades
- **Consecutive losses**: Current streak
- **Volatility**: Current ATR%
- **Spread**: Current bid-ask
- **Data freshness**: Last update time

### Daily Review

Every day:

- Total PnL vs target
- Trade count and frequency
- Circuit breaker triggers
- Max intraday drawdown
- Fee/slippage costs

### Weekly Review

Every week:

- Compare vs backtest expectations
- Sharpe ratio trend
- Parameter effectiveness
- Market regime changes
- Adjust if needed

## Position Sizing Rules

### Standard Mode

100% of available capital (minus reserve):

```python
size = (equity - reserve) / price
```

### Conservative Mode

Cap maximum position:

```python
max_position = equity * 0.50  # 50% max
size = min(calculated_size, max_position / price)
```

**Use when:**
- Learning the system
- Testing new parameters
- Uncertain market conditions
- High volatility

## Correlation Risk

### Single Asset (BTC-USD)

**Pros:**
- Simple to manage
- No correlation complexity
- Clear risk profile

**Cons:**
- No diversification
- Fully exposed to BTC volatility
- Correlation with crypto market = 1.0

### Multi-Asset (Future Enhancement)

If running multiple strategies:

- Monitor correlation between positions
- Avoid over-concentration
- Consider portfolio heat
- Adjust sizing based on correlation

## Counterparty Risk

### Exchange Risk

**Mitigation:**
- Use multiple exchanges
- Withdraw funds regularly
- Keep only working capital on exchange
- Monitor exchange health

**Red flags:**
- Withdrawal delays
- API instability
- Regulatory issues
- Unusual price deviations

### API Key Security

**Best practices:**
- Restrict API permissions (no withdrawals)
- Use IP whitelisting
- Rotate keys regularly
- Store securely (never in git)
- Monitor API usage

## Disaster Recovery

### Backup State

Strategy state is persisted to database:

- Last position entry
- Peak/trough prices
- Realized PnL
- Trade history

**Recovery process:**
1. Check database state
2. Query exchange for actual balances
3. Reconcile positions
4. Resume from correct state

### Lost Connection

If connection lost:

1. **Paper mode**: Simulated prices continue
2. **Live mode**:
   - Orders may still fill
   - Check exchange directly
   - Reconcile state before resuming

### Database Failure

If database unavailable:

1. Trading pauses automatically
2. In-memory state preserved (temporary)
3. Restore from backup
4. Reconcile with exchange

## Testing Risk Controls

### Before Going Live

Test every circuit breaker:

1. **Max drawdown**:
   - Simulate losses in paper mode
   - Verify pause triggers correctly

2. **Consecutive losses**:
   - Force bad trades
   - Confirm counter increments

3. **Daily loss limit**:
   - Simulate large loss
   - Verify resets at midnight

4. **Volatility bounds**:
   - Test with extreme ATR
   - Confirm blocking

5. **Emergency flatten**:
   - Execute in paper mode
   - Verify all positions close

### Ongoing Testing

- Weekly circuit breaker drills
- Monthly emergency flatten test
- Quarterly full disaster recovery

## Risk Reporting

### Automated Alerts

Set up alerts for:

- Circuit breaker triggers
- Drawdown > 10%
- Consecutive losses > 3
- API errors
- Connection issues

**Channels:**
- Email
- SMS (Twilio)
- Slack/Discord
- PagerDuty

### Risk Dashboard

Monitor in Grafana:

- Equity curve
- Drawdown over time
- Win rate trend
- Circuit breaker history
- Risk metrics

## Best Practices

### Start Small

1. Begin with minimum capital
2. Run for 1 week
3. Verify all metrics
4. Gradually increase size

### Never Disable Safety

- Don't disable circuit breakers "just once"
- Don't increase limits "temporarily"
- Don't skip testing "to save time"

### Stay Informed

- Monitor positions regularly
- Review logs daily
- Understand every trade
- Know your risk exposure

### Have an Exit Plan

Before starting:

- Define maximum loss tolerance
- Set profit-taking targets
- Plan shutdown procedure
- Document decision criteria

## Further Reading

- [Strategy Documentation](STRATEGY.md)
- [Backtesting Guide](BACKTESTING.md)
- Industry: "Quantitative Risk Management" (McNeil et al.)
- Industry: "Algorithmic Trading" (Chan)
