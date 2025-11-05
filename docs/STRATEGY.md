# Strategy Documentation

## Volatility Harvesting Strategy

The Volatility Harvester is a systematic mean-reversion strategy designed to profit from Bitcoin's natural price oscillations.

## Core Concept

**Buy low, sell high** - but systematically:

1. **Track the peak price** during flat periods (no position)
2. **Buy when price dips** X% below the peak
3. **Track the trough price** while holding position
4. **Sell when price rebounds** Y% above entry
5. **Repeat** with full capital compounding

## Mathematical Foundation

### Basic Thresholds (Symmetric, X=Y=5%)

- **Buy trigger**: Price = Peak × (1 - 0.05) = 0.95 × Peak
- **Sell trigger**: Price = Entry × (1 + 0.05) = 1.05 × Entry

**Example:**
- Peak = $50,000
- Buy at $47,500 (5% dip)
- Sell at $49,875 (5% above entry)
- Gross gain: 5% on deployed capital
- Net gain ≈ 4.5% after fees (0.5% round-trip)

### Path Dependency

The strategy is path-dependent:

- **Net vs Peak**: Sell at $49,875 is -0.25% vs peak
- **Gains accumulate** through repeated cycles
- **Compounding effect**: Each cycle uses full equity

### Asymmetric Thresholds

You can use different buy/sell thresholds:

- Buy at -5%, Sell at +6%: Wider profit target
- Buy at -4%, Sell at +4%: Faster cycles, more trades
- Buy at -3%, Sell at +7%: Asymmetric risk/reward

## Adaptive Thresholds

### Volatility-Based Adjustment

The strategy adapts to market conditions using ATR (Average True Range):

```
ATR% = (ATR / Current Price) × 100
```

**Mapping:**
- ATR 2.0% → Use min_swing (default 2%)
- ATR 4.0% → Interpolate
- ATR 6.0% → Use max_swing (default 8%)

**Rationale:**
- **Low volatility** (< 2.5%): Reduce thresholds to stay active, avoid missing moves
- **High volatility** (> 6%): Widen thresholds to avoid whipsaws and false signals

### Example Adaptation

| ATR % | Buy Threshold | Sell Threshold | Reasoning |
|-------|---------------|----------------|-----------|
| 1.5%  | 2.0%          | 2.0%          | Choppy - use minimum |
| 3.0%  | 4.0%          | 4.0%          | Normal - interpolated |
| 5.0%  | 6.5%          | 6.5%          | Elevated - wider |
| 8.0%  | 8.0%          | 8.0%          | Extreme - use maximum |

## Position Sizing

### All-In / All-Out

The strategy uses **full compounding**:

```python
deployable_capital = total_equity × (1 - reserve_pct)
position_size = deployable_capital / current_price
```

**Benefits:**
- Maximum compounding
- Simple state management
- No partial position complexity

**Reserve:**
- Keep 5-10% in reserve for emergencies
- Covers fees, slippage, rounding

### Alternative: Tiered Entry

(Optional, configurable):

Split capital into tranches, buy on each 1% step:

- $50,000 → Buy 20% at $49,500
- → Buy 20% at $49,000
- → Buy 20% at $48,500
- → Buy 20% at $48,000
- → Buy 20% at $47,500

**Exit:** Single sell when price rises Y% above weighted average entry.

**Pros:** Better average price, reduced timing risk
**Cons:** More complex, may not fill all tranches

## Fees & Slippage

### Fee Structure

**Maker orders** (limit in book):
- Fee: 0.00-0.40% (exchange dependent)
- Best execution price
- May not fill

**Taker orders** (market / instant):
- Fee: 0.10-0.60%
- Guaranteed fill
- Slippage cost

### Execution Strategy

1. **Try maker first**: Place limit order slightly inside spread (25% from mid)
2. **Wait for fill**: Timeout after 30 seconds
3. **Fallback to taker**: Execute market order if not filled

**Expected fill rate**: ~70% maker, ~30% taker

### Minimum Profitable Move

Round-trip cost (maker entry + maker exit):
```
Total fees = 0.10% + 0.10% = 0.20%
```

Round-trip cost (taker both sides):
```
Total fees = 0.30% + 0.30% = 0.60%
```

**Minimum profitable threshold:**
- Maker-maker: ~0.25% (covers fees + slippage)
- Taker-taker: ~0.75%

**Strategy default (5%)** has 20x cushion for maker, 7x for taker.

## Trend Filter (Optional)

Optional trend filter using moving averages:

```python
if MA(50) > MA(200):
    allow_long_positions = True
else:
    reduce_size or pause
```

**When to use:**
- Strong trending markets
- Want to avoid trading against major trends
- Willing to miss some opportunities

**When NOT to use:**
- Range-bound markets (misses best opportunities)
- Choppy conditions

## Performance Characteristics

### Ideal Market Conditions

**Best:** Oscillating / range-bound markets
- BTC between $40k-$50k for months
- Regular 5-10% swings every few days
- Predictable volatility

**Worst:** Strong unidirectional trends
- BTC $40k → $60k without pullbacks
- Misses the trend (only catches small dips)
- Low trade frequency

### Expected Metrics

**Conservative estimate (5% thresholds, fees included):**

- **Win rate**: 60-70%
- **Avg win**: +4.5%
- **Avg loss**: -2.0% (stopped out / reversed)
- **Trade frequency**: 10-30 trades/month (depends on volatility)
- **Annual return**: 20-40% in favorable conditions
- **Max drawdown**: 10-20%

### Comparison with Buy-and-Hold

**Volatility Harvester:**
- Profits in range-bound markets ✓
- Underperforms in strong trends ✗
- Capital efficient (100% deployed)
- Active management required

**Buy-and-Hold:**
- Captures full uptrend ✓
- Loses in downtrends ✗
- Passive
- Tax efficient (long-term gains)

**Best of both:** Run 50% buy-and-hold, 50% volatility harvesting

## Tuning Parameters

### Buy/Sell Thresholds

**Conservative (3-4%):**
- More trades
- Smaller gains per trade
- Lower drawdown
- Higher fees as % of gains

**Moderate (5-6%):**
- Balanced trade-off
- Default recommendation
- Good risk/reward

**Aggressive (7-10%):**
- Fewer trades
- Larger gains per trade
- Higher drawdown
- Lower fees as % of gains

### Test Before Deploying

Always backtest parameter changes:

```bash
# Test 3% vs 5% vs 7%
make backtest BUY_THRESHOLD_PCT=3.0 SELL_THRESHOLD_PCT=3.0
make backtest BUY_THRESHOLD_PCT=5.0 SELL_THRESHOLD_PCT=5.0
make backtest BUY_THRESHOLD_PCT=7.0 SELL_THRESHOLD_PCT=7.0
```

## Advanced Variations

### Dynamic Position Sizing

Adjust position size based on volatility:
- High ATR → Reduce size
- Low ATR → Increase size

### Multi-Asset

Run on multiple assets:
- BTC-USD (50% capital)
- ETH-USD (30% capital)
- Other alts (20% capital)

### Mean Reversion + Momentum

Combine with trend following:
- Volatility harvesting in ranges
- Momentum following in trends
- Switch based on regime detection

## Further Reading

- [Backtesting Guide](BACKTESTING.md)
- [Risk Management](RISK.md)
- Research: "Volatility Harvesting in Crypto Markets" (various papers)
