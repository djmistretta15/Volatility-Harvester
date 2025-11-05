import { useState, useEffect } from 'react';
import {
  DollarSign, TrendingUp, Target, AlertCircle, Play, Square,
  Activity, Zap, Shield, BarChart3
} from 'lucide-react';
import { MetricCard } from './MetricCard';
import { EquityChart } from './EquityChart';
import { TradeFeed } from './TradeFeed';
import { StatusIndicator } from './StatusIndicator';
import { ControlPanel } from './ControlPanel';
import { RiskDashboard } from './RiskDashboard';
import { api } from '../services/api';
import { TradingStatus, Trade, EquityPoint } from '../types';
import { formatCurrency, formatPercent, formatBTC } from '../utils/format';

export function Dashboard() {
  const [status, setStatus] = useState<TradingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [equityHistory, setEquityHistory] = useState<EquityPoint[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);

  // Poll status every 2 seconds
  useEffect(() => {
    let interval: number;

    const fetchStatus = async () => {
      try {
        const data = await api.getStatus();
        setStatus(data);
        setError(null);

        // Update equity history
        setEquityHistory(prev => [
          ...prev,
          {
            timestamp: new Date().toISOString(),
            equity: data.equity,
            drawdown: data.drawdown_pct
          }
        ].slice(-100)); // Keep last 100 points

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch status');
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    interval = window.setInterval(fetchStatus, 2000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-12 h-12 animate-pulse text-primary-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error && !status) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md">
          <AlertCircle className="w-12 h-12 text-danger-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2 text-center">Connection Error</h2>
          <p className="text-gray-600 text-center">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 w-full px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const totalPnL = (status?.realized_pnl || 0) + (status?.unrealized_pnl || 0);
  const pnlPercent = status ? (totalPnL / status.equity) * 100 : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-100 to-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-500 rounded-lg">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Volatility Harvester</h1>
                <p className="text-sm text-gray-500">BTC Trading Engine</p>
              </div>
            </div>

            <StatusIndicator status={status} />
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Control Panel */}
        <div className="mb-6">
          <ControlPanel status={status} onUpdate={() => window.location.reload()} />
        </div>

        {/* Main Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          <MetricCard
            title="Total Equity"
            value={formatCurrency(status?.equity || 0)}
            change={formatPercent(pnlPercent)}
            changeType={pnlPercent > 0 ? 'positive' : pnlPercent < 0 ? 'negative' : 'neutral'}
            icon={DollarSign}
            iconColor="text-primary-600"
            subtitle="USD"
          />

          <MetricCard
            title="Realized P&L"
            value={formatCurrency(status?.realized_pnl || 0)}
            icon={TrendingUp}
            iconColor={status && status.realized_pnl > 0 ? 'text-success-600' : 'text-danger-600'}
            subtitle={`${status?.total_trades || 0} trades`}
          />

          <MetricCard
            title="Win Rate"
            value={`${(status?.win_rate || 0).toFixed(1)}%`}
            icon={Target}
            iconColor="text-warning-600"
            trend={
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-success-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${status?.win_rate || 0}%` }}
                  />
                </div>
              </div>
            }
          />

          <MetricCard
            title="Max Drawdown"
            value={formatPercent(status?.drawdown_pct || 0)}
            icon={Shield}
            iconColor="text-danger-600"
            changeType={status && status.drawdown_pct > 10 ? 'negative' : 'positive'}
          />
        </div>

        {/* Charts and Risk */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="lg:col-span-2">
            <EquityChart data={equityHistory} />
          </div>

          <div>
            <RiskDashboard status={status} />
          </div>
        </div>

        {/* Position and Trades */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Position</h3>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <span className="text-gray-600">State</span>
                <span className={`font-semibold uppercase px-3 py-1 rounded-full text-sm ${
                  status?.state === 'long'
                    ? 'bg-success-100 text-success-700'
                    : 'bg-gray-200 text-gray-700'
                }`}>
                  {status?.state || 'Unknown'}
                </span>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <span className="text-gray-600">Cash (USD)</span>
                <span className="font-semibold text-gray-900">{formatCurrency(status?.cash || 0)}</span>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <span className="text-gray-600">BTC Holdings</span>
                <span className="font-semibold text-gray-900">{formatBTC(status?.btc || 0)}</span>
              </div>

              <div className="flex items-center justify-between p-4 bg-primary-50 rounded-lg border border-primary-200">
                <span className="text-primary-700 font-medium">Unrealized P&L</span>
                <span className={`font-bold ${
                  status && status.unrealized_pnl > 0
                    ? 'text-success-600'
                    : status && status.unrealized_pnl < 0
                    ? 'text-danger-600'
                    : 'text-gray-600'
                }`}>
                  {formatCurrency(status?.unrealized_pnl || 0)}
                </span>
              </div>
            </div>
          </div>

          <TradeFeed trades={trades} />
        </div>
      </div>
    </div>
  );
}
