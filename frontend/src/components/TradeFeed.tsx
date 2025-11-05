import { TrendingUp, TrendingDown, Clock } from 'lucide-react';
import { Trade } from '../types';
import { formatCurrency, formatBTC, formatTime, formatPercent } from '../utils/format';

interface TradeFeedProps {
  trades: Trade[];
  maxItems?: number;
}

export function TradeFeed({ trades, maxItems = 10 }: TradeFeedProps) {
  const recentTrades = trades.slice(-maxItems).reverse();

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Live Trade Feed</h3>
          <p className="text-sm text-gray-500">Recent executions with P&L</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Clock className="w-4 h-4" />
          <span>Real-time</span>
        </div>
      </div>

      <div className="space-y-3">
        {recentTrades.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <TrendingUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No trades yet. Waiting for signals...</p>
          </div>
        ) : (
          recentTrades.map((trade, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-4 rounded-lg border border-gray-100 hover:border-gray-200 transition-all duration-200 animate-fade-in"
            >
              <div className="flex items-center gap-4">
                <div className={`p-2 rounded-lg ${
                  trade.side === 'buy'
                    ? 'bg-success-50'
                    : 'bg-danger-50'
                }`}>
                  {trade.side === 'buy' ? (
                    <TrendingUp className="w-5 h-5 text-success-600" />
                  ) : (
                    <TrendingDown className="w-5 h-5 text-danger-600" />
                  )}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className={`font-semibold uppercase text-sm ${
                      trade.side === 'buy' ? 'text-success-700' : 'text-danger-700'
                    }`}>
                      {trade.side}
                    </span>
                    <span className="text-gray-400">•</span>
                    <span className="text-sm text-gray-600">{formatBTC(trade.qty)}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                      {trade.is_maker ? 'Maker' : 'Taker'}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {formatTime(trade.timestamp)} • {formatCurrency(trade.price)}
                  </div>
                </div>
              </div>

              <div className="text-right">
                {trade.pnl !== undefined && (
                  <div className={`font-semibold ${
                    trade.pnl > 0 ? 'text-success-600' : trade.pnl < 0 ? 'text-danger-600' : 'text-gray-600'
                  }`}>
                    {trade.pnl > 0 ? '+' : ''}{formatCurrency(trade.pnl)}
                  </div>
                )}
                <div className="text-xs text-gray-500">
                  Fee: {formatCurrency(trade.fee)}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {recentTrades.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-gray-900">{recentTrades.length}</div>
              <div className="text-xs text-gray-500">Total Trades</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-success-600">
                {recentTrades.filter(t => t.pnl && t.pnl > 0).length}
              </div>
              <div className="text-xs text-gray-500">Winners</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-danger-600">
                {recentTrades.filter(t => t.pnl && t.pnl < 0).length}
              </div>
              <div className="text-xs text-gray-500">Losers</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
