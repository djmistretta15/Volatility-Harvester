# Backtesting Guide

## Overview

The Volatility Harvester includes a comprehensive backtesting engine that simulates the strategy on historical data.

## Quick Start

### Basic Backtest

```bash
# Via Make
make backtest

# Via API
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

### Sample Output

```json
{
  "initial_capital": 10000.0,
  "final_capital": 13245.67,
  "total_pnl": 3245.67,
  "total_pnl_pct": 32.46,
  "total_trades": 45,
  "winning_trades": 32,
  "losing_trades": 13,
  "win_rate": 71.11,
  "avg_win": 156.32,
  "avg_loss": -89.45,
  "max_drawdown_pct": 12.34,
  "sharpe_ratio": 1.89,
  "sortino_ratio": 2.67,
  "cagr": 29.87,
  "total_fees_paid": 234.56,
  "exposure_pct": 68.5
}
```

## Understanding Results

### Return Metrics

**Total PnL**
- Absolute dollar gain/loss
- Final equity - Initial capital

**Total PnL %**
- Percentage return on initial capital
- (Final / Initial - 1) × 100

**CAGR (Compound Annual Growth Rate)**
- Annualized return
- Accounts for compounding
- Comparable across different time periods

**Formula:**
```
CAGR = ((Final / Initial) ^ (1 / Years)) - 1
```

### Risk-Adjusted Returns

**Sharpe Ratio**
- Return per unit of risk
- Higher is better (> 1.0 is good, > 2.0 is excellent)
- Formula: (Mean Return / Std Dev of Returns) × √252

**Sortino Ratio**
- Like Sharpe but only penalizes downside volatility
- More relevant for asymmetric strategies
- Higher is better

**Max Drawdown**
- Largest peak-to-trough decline
- Key risk metric
- Lower is better (< 20% is good)

### Trade Statistics

**Total Trades**
- Number of complete round trips (entry + exit)
- Higher frequency = more opportunities but more fees

**Win Rate**
- % of profitable trades
- 60-70% is typical for mean reversion
- Don't chase 90%+ (likely curve-fit)

**Average Win / Loss**
- Avg profit on winning trades
- Avg loss on losing trades
- Ratio > 1.5 is healthy

**Profit Factor**
- Total wins / Total losses
- > 1.5 is good, > 2.0 is excellent

**Exposure**
- % of time with open position
- High exposure = capital efficient
- Lower exposure = more selective

## Parameter Optimization

### Single Parameter Test

Test one parameter at a time:

```bash
# Test buy threshold
for threshold in 3 4 5 6 7; do
  curl -X POST http://localhost:8000/backtest \
    -d "{\"buy_threshold_pct\": $threshold, \"sell_threshold_pct\": $threshold}"
done
```

### Parameter Sweep

Test multiple combinations:

```python
from app.services.backtester import Backtester, BacktestConfig
import pandas as pd

# Load candles
candles = load_historical_data()

# Define parameter grid
buy_thresholds = [2, 3, 4, 5, 6, 7, 8]
sell_thresholds = [2, 3, 4, 5, 6, 7, 8]

# Run sweep
results = []
for buy in buy_thresholds:
    for sell in sell_thresholds:
        config = BacktestConfig(
            buy_threshold_pct=buy,
            sell_threshold_pct=sell,
            adaptive_thresholds=False
        )
        backtester = Backtester(config)
        result = backtester.run(candles)
        results.append({
            'buy': buy,
            'sell': sell,
            'pnl_pct': result.total_pnl_pct,
            'sharpe': result.sharpe_ratio,
            'max_dd': result.max_drawdown_pct
        })

# Analyze
df = pd.DataFrame(results)
print(df.sort_values('sharpe', ascending=False).head(10))
```

### Heatmap Visualization

```python
import seaborn as sns
import matplotlib.pyplot as plt

# Create pivot table
pivot = df.pivot(index='buy', columns='sell', values='sharpe')

# Plot heatmap
plt.figure(figsize=(10, 8))
sns.heatmap(pivot, annot=True, fmt='.2f', cmap='RdYlGn')
plt.title('Sharpe Ratio by Buy/Sell Thresholds')
plt.xlabel('Sell Threshold %')
plt.ylabel('Buy Threshold %')
plt.savefig('parameter_heatmap.png')
```

## Walk-Forward Analysis

Test robustness by training on one period and testing on next:

```python
periods = [
    ('2022-01-01', '2022-06-30'),  # Train
    ('2022-07-01', '2022-12-31'),  # Test
    ('2023-01-01', '2023-06-30'),  # Train
    ('2023-07-01', '2023-12-31'),  # Test
]

for i in range(0, len(periods), 2):
    train_start, train_end = periods[i]
    test_start, test_end = periods[i+1]

    # Optimize on training period
    best_params = optimize_parameters(train_start, train_end)

    # Test on out-of-sample period
    result = backtest(test_start, test_end, best_params)

    print(f"Test {test_start} to {test_end}:")
    print(f"  PnL: {result.total_pnl_pct:.2f}%")
    print(f"  Sharpe: {result.sharpe_ratio:.2f}")
```

## Overfitting Detection

### Signs of Overfitting

⚠️ **Red flags:**

1. **Perfect backtest** (> 100% annual return with < 5% drawdown)
   - Likely curve-fit to historical data
   - Won't generalize to future

2. **Too many parameters**
   - > 5-6 tunable parameters
   - Easy to find combinations that work in past

3. **Extreme parameter values**
   - Buy at 0.5%, Sell at 12.3%
   - Odd numbers suggest optimization artifact

4. **Large train/test divergence**
   - Great on training data
   - Poor on test data
   - Classic overfitting

### Prevention

✅ **Best practices:**

1. **Keep it simple**
   - Limit to 2-3 core parameters
   - Use round numbers (5%, not 5.37%)

2. **Out-of-sample testing**
   - Reserve 30% of data for final test
   - Never optimize on test data

3. **Walk-forward validation**
   - Test on multiple periods
   - Consistent performance > peak performance

4. **Monte Carlo simulation**
   - Shuffle trade order
   - Test robustness to sequence

5. **Regime analysis**
   - Test in bull/bear/sideways separately
   - Understand where strategy works

## Regime Analysis

### Bull Market (Uptrend)

**Characteristics:**
- Price mostly rising
- Dips are shallow and brief
- Strategy underperforms buy-and-hold

**Expected:**
- Lower trade frequency
- Smaller gains per trade
- May miss big moves

### Bear Market (Downtrend)

**Characteristics:**
- Price mostly falling
- Rallies are brief and weak
- Strategy catches falling knives

**Expected:**
- Higher trade frequency
- Mix of wins (bounces) and losses (continued fall)
- Potential for drawdown

### Sideways Market (Range)

**Characteristics:**
- Price oscillates in range
- Clear support/resistance
- **IDEAL for this strategy**

**Expected:**
- High trade frequency
- Consistent gains
- Best risk/reward

### How to Analyze

```python
# Identify regime
candles['ma_50'] = candles['close'].rolling(50).mean()
candles['ma_200'] = candles['close'].rolling(200).mean()

candles['regime'] = 'sideways'
candles.loc[candles['ma_50'] > candles['ma_200'] * 1.05, 'regime'] = 'bull'
candles.loc[candles['ma_50'] < candles['ma_200'] * 0.95, 'regime'] = 'bear'

# Backtest by regime
for regime in ['bull', 'bear', 'sideways']:
    regime_candles = candles[candles['regime'] == regime]
    result = backtest(regime_candles)
    print(f"{regime}: PnL = {result.total_pnl_pct:.2f}%")
```

## Common Issues & Solutions

### Issue: Low Trade Frequency

**Symptoms:**
- Only 2-3 trades per month
- Long flat periods

**Causes:**
- Thresholds too wide
- Market trending (no dips/rallies)
- Low volatility

**Solutions:**
- Reduce thresholds (but not below fee breakeven)
- Enable adaptive mode
- Wait for better market conditions

### Issue: High Drawdown

**Symptoms:**
- Drawdown > 20%
- Multiple consecutive losses

**Causes:**
- Thresholds too tight (whipsaws)
- Strong trend against position
- Poor risk management

**Solutions:**
- Widen thresholds
- Enable trend filter
- Reduce position size
- Add circuit breakers

### Issue: Underperforming Buy-and-Hold

**Symptoms:**
- Strategy return < holding BTC

**Context:**
- This is EXPECTED in strong bull markets
- Strategy is not designed to beat trending markets

**Solutions:**
- Accept as trade-off for downside protection
- Run 50% strategy / 50% hold
- Focus on risk-adjusted returns (Sharpe)

### Issue: Low Win Rate

**Symptoms:**
- Win rate < 50%

**Causes:**
- Stops too tight
- Taking profits too late
- Trend persistence

**Solutions:**
- Widen stops
- Take profits earlier
- Add trend filter

## Comparing Configurations

### Scenario Testing

Test different market scenarios:

| Scenario | Buy % | Sell % | Adaptive | Expected |
|----------|-------|--------|----------|----------|
| Conservative | 6.0 | 6.0 | No | Low risk, low return |
| Moderate | 5.0 | 5.0 | Yes | Balanced |
| Aggressive | 3.0 | 3.0 | No | High risk, high return |
| Asymmetric | 5.0 | 7.0 | Yes | Wider targets |

### Performance Comparison

```
Configuration     | PnL %  | Sharpe | Max DD | Trades
------------------|--------|--------|--------|-------
Conservative      | +18.2% |  1.45  |  8.3%  |   22
Moderate          | +28.5% |  1.92  | 12.1%  |   38
Aggressive        | +35.7% |  1.68  | 18.9%  |   67
Asymmetric        | +31.2% |  1.87  | 14.2%  |   29
Buy-and-Hold      | +42.1% |  1.23  | 25.6%  |    0
```

**Interpretation:**
- Aggressive has highest return but also highest drawdown
- Moderate has best Sharpe (risk-adjusted)
- Buy-and-hold beats all (bull market)
- But strategy has lower drawdown (better risk)

## Generating Reports

### CSV Export

```python
# Export trades
result = backtest(candles)
trades_df = pd.DataFrame(result.trades)
trades_df.to_csv('backtest_trades.csv', index=False)

# Export equity curve
result.equity_curve.to_csv('equity_curve.csv')
```

### Visualization

```python
import matplotlib.pyplot as plt

# Plot equity curve
plt.figure(figsize=(12, 6))
plt.plot(result.equity_curve.index, result.equity_curve['equity'])
plt.title('Equity Curve')
plt.xlabel('Date')
plt.ylabel('Equity ($)')
plt.grid(True)
plt.savefig('equity_curve.png')

# Plot drawdown
equity = result.equity_curve['equity']
peak = equity.expanding().max()
drawdown = (equity - peak) / peak * 100

plt.figure(figsize=(12, 4))
plt.fill_between(drawdown.index, drawdown, 0, color='red', alpha=0.3)
plt.title('Drawdown Over Time')
plt.xlabel('Date')
plt.ylabel('Drawdown %')
plt.grid(True)
plt.savefig('drawdown.png')
```

## Next Steps

After successful backtesting:

1. ✅ **Validate results**
   - Check for overfitting
   - Test on out-of-sample data
   - Verify fee calculations

2. ✅ **Paper trade**
   - Run for 1-2 weeks
   - Compare actual vs expected results
   - Verify execution logic

3. ✅ **Start live (small)**
   - Begin with minimum capital
   - Monitor closely
   - Scale up gradually

## Further Reading

- [Strategy Documentation](STRATEGY.md)
- [Risk Management](RISK.md)
- Book: "Quantitative Trading" by Ernest Chan
- Book: "Algorithmic Trading" by Jeffrey Bacidore
