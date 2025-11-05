# Sample Backtest Report

## Configuration

**Test Period:** January 1, 2023 - December 31, 2023
**Initial Capital:** $10,000.00
**Symbol:** BTC-USD
**Exchange:** Coinbase Advanced (simulated)

### Strategy Parameters

| Parameter | Value |
|-----------|-------|
| Buy Threshold | 5.0% |
| Sell Threshold | 5.0% |
| Adaptive Thresholds | Enabled |
| Min Swing | 2.0% |
| Max Swing | 8.0% |
| Reserve % | 8.0% |
| Maker Fee | 0.10% |
| Taker Fee | 0.30% |

## Summary Results

### Performance Metrics

| Metric | Value |
|--------|-------|
| Initial Capital | $10,000.00 |
| Final Capital | $13,456.78 |
| Total PnL | $3,456.78 |
| Total Return | **+34.57%** |
| CAGR | 34.57% |
| Buy & Hold Return | +42.10% |

### Risk Metrics

| Metric | Value |
|--------|-------|
| Max Drawdown | 12.34% |
| Sharpe Ratio | 1.89 |
| Sortino Ratio | 2.67 |
| Win Rate | 71.11% |

### Trading Statistics

| Metric | Value |
|--------|-------|
| Total Trades | 45 |
| Winning Trades | 32 |
| Losing Trades | 13 |
| Avg Win | $156.32 |
| Avg Loss | -$89.45 |
| Profit Factor | 1.85 |
| Total Fees Paid | $234.56 |
| Exposure | 68.5% |

## Monthly Breakdown

| Month | Trades | PnL | PnL % | Drawdown |
|-------|--------|-----|-------|----------|
| Jan 2023 | 4 | $287.45 | +2.87% | -3.2% |
| Feb 2023 | 3 | $412.89 | +4.01% | -1.8% |
| Mar 2023 | 5 | -$156.23 | -1.48% | -5.6% |
| Apr 2023 | 2 | $189.67 | +1.86% | -2.1% |
| May 2023 | 6 | $523.45 | +4.98% | -4.2% |
| Jun 2023 | 4 | $198.34 | +1.78% | -3.5% |
| Jul 2023 | 3 | $267.12 | +2.41% | -2.9% |
| Aug 2023 | 5 | $445.67 | +3.89% | -6.1% |
| Sep 2023 | 2 | -$234.56 | -1.98% | -8.4% |
| Oct 2023 | 4 | $678.90 | +5.87% | -4.7% |
| Nov 2023 | 3 | $512.34 | +4.23% | -3.8% |
| Dec 2023 | 4 | $331.74 | +2.63% | -2.6% |

## Sample Trades

### Best Trades

| Date | Type | Entry | Exit | PnL | % Gain |
|------|------|-------|------|-----|--------|
| May 15 | BUY→SELL | $26,450 | $27,772 | $456.78 | +5.0% |
| Oct 21 | BUY→SELL | $29,200 | $30,660 | $523.89 | +5.0% |
| Aug 8 | BUY→SELL | $28,100 | $29,505 | $489.12 | +5.0% |

### Worst Trades

| Date | Type | Entry | Exit | PnL | % Loss |
|------|------|-------|------|-----|---------|
| Sep 12 | BUY→SELL | $25,800 | $25,284 | -$189.45 | -2.0% |
| Mar 18 | BUY→SELL | $27,600 | $26,796 | -$234.67 | -2.9% |
| Jun 5 | BUY→SELL | $30,200 | $29,596 | -$156.89 | -2.0% |

## Performance Chart (ASCII)

### Equity Curve

```
$14,000 |                                    •
        |                               •   ••
$13,000 |                          •  •   •
        |                      • •  •
$12,000 |                  • •
        |              • •
$11,000 |          • •
        |      • •
$10,000 | • •
        |
$9,000  +--------------------------------
         Jan  Mar  May  Jul  Sep  Nov
```

### Drawdown Chart

```
   0% |••  •  ••••  •••  •••••  ••••
      |  ••          •            •
  -5% |     •           •
      |
 -10% |                    •
      |
 -15% +--------------------------------
       Jan  Mar  May  Jul  Sep  Nov
```

## Market Regime Analysis

### By Volatility Regime

| Regime | Trades | Win Rate | Avg Return | Sharpe |
|--------|--------|----------|------------|--------|
| Low Vol (ATR < 2.5%) | 8 | 62.5% | +2.8% | 1.34 |
| Normal Vol (2.5-5%) | 28 | 75.0% | +4.2% | 2.15 |
| High Vol (> 5%) | 9 | 66.7% | +3.5% | 1.56 |

### By Market Trend

| Trend | Trades | Win Rate | Avg Return | Notes |
|-------|--------|----------|------------|-------|
| Bull Market | 18 | 66.7% | +3.8% | Fewer dips, longer waits |
| Bear Market | 12 | 58.3% | +2.1% | More whipsaws |
| Sideways | 15 | 86.7% | +5.4% | **Optimal conditions** |

## Circuit Breaker Events

| Date | Type | Reason | Duration |
|------|------|--------|----------|
| Mar 20 | Consecutive Losses | 5 losses in a row | 2 days |
| Sep 15 | Volatility Bound | ATR > 10% (extreme) | 1 day |

**Total Paused Days:** 3 days (0.8% of year)

## Fee Analysis

| Type | Count | Total Fees |
|------|-------|------------|
| Maker Orders | 63 (70%) | $98.45 |
| Taker Orders | 27 (30%) | $136.11 |
| **Total** | **90** | **$234.56** |

**Fee Impact:** Fees reduced returns by 2.35%

## Parameter Sensitivity

### Threshold Heatmap (Sharpe Ratio)

```
Sell%  2.0   3.0   4.0   5.0   6.0   7.0   8.0
Buy%
2.0    1.12  1.34  1.56  1.67  1.58  1.42  1.23
3.0    1.23  1.45  1.72  1.81  1.76  1.61  1.44
4.0    1.34  1.58  1.84  1.92  1.89  1.78  1.62
5.0    1.42  1.67  1.89  [1.89] 1.91  1.82  1.70
6.0    1.38  1.61  1.82  1.91  1.87  1.79  1.68
7.0    1.29  1.52  1.71  1.78  1.76  1.71  1.63
8.0    1.18  1.39  1.58  1.64  1.62  1.59  1.54
```

**Optimal:** 5% buy / 5-6% sell (current configuration)

## Comparison with Benchmarks

| Strategy | Return | Sharpe | Max DD | Winner |
|----------|--------|--------|--------|---------|
| Volatility Harvester | +34.57% | 1.89 | 12.34% | ✓ Risk-Adjusted |
| Buy & Hold BTC | +42.10% | 1.23 | 25.68% | ✓ Raw Return |
| 60/40 Portfolio | +12.45% | 0.98 | 8.92% | ✓ Low Risk |
| S&P 500 | +18.23% | 1.45 | 10.12% | - |

## Observations

### What Worked

1. **Sideways markets**: 86.7% win rate in range-bound conditions
2. **Adaptive thresholds**: Captured moves in varying volatility
3. **Maker-first execution**: 70% maker fill rate reduced fees significantly
4. **Circuit breakers**: Protected from extended drawdowns

### What Didn't Work

1. **Strong trends**: Underperformed buy-and-hold in uptrends
2. **Whipsaws in September**: High volatility caused false signals
3. **Slow recovery**: March losses took time to recover

### Recommendations

1. ✅ **Deploy to paper trading** - Results are solid and consistent
2. ✅ **Start with small capital** - Test real execution
3. ⚠️ **Monitor in strong trends** - Consider partial buy-and-hold allocation
4. ✅ **Keep current parameters** - 5%/5% thresholds are near optimal
5. ✅ **Enable adaptive mode** - Performed better than fixed thresholds

## Risk Assessment

| Risk Factor | Level | Mitigation |
|-------------|-------|------------|
| Max Drawdown | Low (12%) | Well within 20% limit |
| Consecutive Losses | Medium | Max 5 observed, managed |
| Fee Impact | Low | 2.35% drag, acceptable |
| Trend Risk | High | Underperforms in trends |
| Execution Risk | Low | Good fill rates |

## Next Steps

1. **Paper Trade**: Run for 2 weeks with same parameters
2. **Monitor**: Track actual fills, fees, and slippage
3. **Validate**: Compare paper results vs backtest expectations
4. **Go Live**: Start with $1,000 capital if paper validates
5. **Scale**: Gradually increase after 1 month of stable performance

---

**Generated:** 2025-01-15 14:32:00 UTC
**Backtest Engine:** Volatility Harvester v1.0.0
**Data Source:** Coinbase Advanced (1-minute candles)

*Disclaimer: Past performance does not guarantee future results. This is a simulation on historical data.*
