import { Activity, Pause, AlertTriangle } from 'lucide-react';
import { TradingStatus } from '../types';

interface StatusIndicatorProps {
  status: TradingStatus | null;
}

export function StatusIndicator({ status }: StatusIndicatorProps) {
  if (!status) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg">
        <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" />
        <span className="text-sm font-medium text-gray-600">Connecting...</span>
      </div>
    );
  }

  if (status.paused) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-warning-50 border border-warning-200 rounded-lg">
        <Pause className="w-4 h-4 text-warning-600" />
        <div>
          <div className="text-sm font-medium text-warning-700">Paused</div>
          {status.pause_reason && (
            <div className="text-xs text-warning-600">{status.pause_reason}</div>
          )}
        </div>
      </div>
    );
  }

  if (!status.running) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg">
        <div className="w-2 h-2 rounded-full bg-gray-400" />
        <span className="text-sm font-medium text-gray-600">Stopped</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-success-50 border border-success-200 rounded-lg">
      <div className="w-2 h-2 rounded-full bg-success-500 animate-pulse-slow" />
      <Activity className="w-4 h-4 text-success-600 animate-pulse" />
      <span className="text-sm font-medium text-success-700">Active</span>
    </div>
  );
}
