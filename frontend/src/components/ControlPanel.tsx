import { useState } from 'react';
import { Play, Square, AlertTriangle, Zap } from 'lucide-react';
import { TradingStatus } from '../types';
import { api } from '../services/api';

interface ControlPanelProps {
  status: TradingStatus | null;
  onUpdate: () => void;
}

export function ControlPanel({ status, onUpdate }: ControlPanelProps) {
  const [loading, setLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleStart = async (mode: 'paper' | 'live') => {
    if (mode === 'live' && !showConfirm) {
      setShowConfirm(true);
      return;
    }

    setLoading(true);
    try {
      await api.startTrading(mode);
      onUpdate();
      setShowConfirm(false);
    } catch (error) {
      alert(`Failed to start: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await api.stopTrading();
      onUpdate();
    } catch (error) {
      alert(`Failed to stop: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleEmergencyFlatten = async () => {
    if (!confirm('⚠️ EMERGENCY FLATTEN - This will sell ALL positions immediately at market price. Are you sure?')) {
      return;
    }

    setLoading(true);
    try {
      await api.emergencyFlatten();
      onUpdate();
    } catch (error) {
      alert(`Failed to flatten: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Trading Controls</h2>
          <p className="text-sm text-gray-500">Manage your trading session</p>
        </div>

        <div className="flex items-center gap-3">
          {!status?.running ? (
            <>
              <button
                onClick={() => handleStart('paper')}
                disabled={loading}
                className="flex items-center gap-2 px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-4 h-4" />
                Start Paper Trading
              </button>

              {showConfirm ? (
                <div className="flex items-center gap-2 px-4 py-2 bg-danger-50 border border-danger-200 rounded-lg">
                  <AlertTriangle className="w-4 h-4 text-danger-600" />
                  <span className="text-sm text-danger-700 mr-2">Real money!</span>
                  <button
                    onClick={() => handleStart('live')}
                    disabled={loading}
                    className="px-4 py-1 bg-danger-500 hover:bg-danger-600 text-white text-sm font-medium rounded transition-colors"
                  >
                    Confirm Live
                  </button>
                  <button
                    onClick={() => setShowConfirm(false)}
                    className="px-4 py-1 bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm font-medium rounded transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowConfirm(true)}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-3 bg-danger-500 hover:bg-danger-600 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
                >
                  <Zap className="w-4 h-4" />
                  Start Live Trading
                </button>
              )}
            </>
          ) : (
            <>
              <button
                onClick={handleStop}
                disabled={loading}
                className="flex items-center gap-2 px-6 py-3 bg-gray-500 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
              >
                <Square className="w-4 h-4" />
                Stop Trading
              </button>

              {status.state === 'long' && (
                <button
                  onClick={handleEmergencyFlatten}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-3 bg-danger-600 hover:bg-danger-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
                >
                  <AlertTriangle className="w-4 h-4" />
                  Emergency Flatten
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {showConfirm && !status?.running && (
        <div className="mt-4 p-4 bg-warning-50 border border-warning-200 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-warning-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-warning-800">
              <p className="font-semibold mb-1">⚠️ Live Trading Warning</p>
              <p>Live trading uses real money and real exchange orders. Make sure you have:</p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-warning-700">
                <li>Tested thoroughly in paper mode</li>
                <li>Configured proper risk limits</li>
                <li>Started with small capital</li>
                <li>Set up monitoring and alerts</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
