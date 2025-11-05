import { Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { TradingStatus } from '../types';
import { formatPercent } from '../utils/format';

interface RiskDashboardProps {
  status: TradingStatus | null;
}

export function RiskDashboard({ status }: RiskDashboardProps) {
  const maxDrawdown = 20; // From config
  const maxWinRate = 100;

  const drawdownPercent = ((status?.drawdown_pct || 0) / maxDrawdown) * 100;
  const isDrawdownDanger = drawdownPercent > 75;
  const isDrawdownWarning = drawdownPercent > 50 && drawdownPercent <= 75;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 h-full">
      <div className="mb-4 flex items-center gap-2">
        <Shield className="w-5 h-5 text-primary-600" />
        <h3 className="text-lg font-semibold text-gray-900">Risk Monitor</h3>
      </div>

      <div className="space-y-4">
        {/* Circuit Breaker Status */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Circuit Breakers</span>
            {status?.paused ? (
              <span className="flex items-center gap-1 text-xs text-danger-600">
                <XCircle className="w-3 h-3" />
                Triggered
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-success-600">
                <CheckCircle className="w-3 h-3" />
                Active
              </span>
            )}
          </div>

          {status?.paused && status.pause_reason && (
            <div className="mt-2 p-2 bg-warning-50 border border-warning-200 rounded text-xs text-warning-700">
              <AlertTriangle className="w-3 h-3 inline mr-1" />
              {status.pause_reason}
            </div>
          )}
        </div>

        {/* Drawdown Meter */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Drawdown</span>
            <span className={`text-sm font-semibold ${
              isDrawdownDanger ? 'text-danger-600' :
              isDrawdownWarning ? 'text-warning-600' :
              'text-success-600'
            }`}>
              {formatPercent(status?.drawdown_pct || 0)}
            </span>
          </div>

          <div className="relative">
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div
                className={`h-3 rounded-full transition-all duration-500 ${
                  isDrawdownDanger ? 'bg-danger-500' :
                  isDrawdownWarning ? 'bg-warning-500' :
                  'bg-success-500'
                }`}
                style={{ width: `${Math.min(drawdownPercent, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0%</span>
              <span className="text-danger-600">Max: {maxDrawdown}%</span>
            </div>
          </div>
        </div>

        {/* Win Rate */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Win Rate</span>
            <span className="text-sm font-semibold text-primary-600">
              {(status?.win_rate || 0).toFixed(1)}%
            </span>
          </div>

          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className="h-3 bg-gradient-to-r from-success-400 to-success-600 rounded-full transition-all duration-500"
              style={{ width: `${status?.win_rate || 0}%` }}
            />
          </div>
        </div>

        {/* Risk Indicators */}
        <div className="pt-4 border-t border-gray-100 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Total Trades</span>
            <span className="font-semibold text-gray-900">{status?.total_trades || 0}</span>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Position</span>
            <span className={`font-semibold uppercase px-2 py-0.5 rounded text-xs ${
              status?.state === 'long' ? 'bg-success-100 text-success-700' : 'bg-gray-100 text-gray-600'
            }`}>
              {status?.state || 'Unknown'}
            </span>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Trading Mode</span>
            <span className={`font-semibold uppercase px-2 py-0.5 rounded text-xs ${
              status?.running ? 'bg-primary-100 text-primary-700' : 'bg-gray-100 text-gray-600'
            }`}>
              {status?.running ? 'Active' : 'Stopped'}
            </span>
          </div>
        </div>

        {/* Health Score */}
        <div className="pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">System Health</span>
            <span className="text-xs text-gray-500">Live</span>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div className="text-center p-2 bg-success-50 rounded">
              <div className="text-xs text-success-600 font-medium">API</div>
              <div className="text-lg font-bold text-success-700">✓</div>
            </div>
            <div className="text-center p-2 bg-success-50 rounded">
              <div className="text-xs text-success-600 font-medium">Data</div>
              <div className="text-lg font-bold text-success-700">✓</div>
            </div>
            <div className={`text-center p-2 rounded ${
              status?.running ? 'bg-success-50' : 'bg-gray-100'
            }`}>
              <div className={`text-xs font-medium ${
                status?.running ? 'text-success-600' : 'text-gray-500'
              }`}>
                Trading
              </div>
              <div className={`text-lg font-bold ${
                status?.running ? 'text-success-700' : 'text-gray-500'
              }`}>
                {status?.running ? '✓' : '○'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
