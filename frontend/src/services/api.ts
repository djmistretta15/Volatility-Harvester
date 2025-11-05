import type { TradingStatus, Config, BacktestResult } from '../types';

const API_BASE = '/api';

export const api = {
  async getStatus(): Promise<TradingStatus> {
    const res = await fetch(`${API_BASE}/status`);
    if (!res.ok) throw new Error('Failed to fetch status');
    return res.json();
  },

  async getConfig(): Promise<Config> {
    const res = await fetch(`${API_BASE}/config`);
    if (!res.ok) throw new Error('Failed to fetch config');
    return res.json();
  },

  async startTrading(mode: 'paper' | 'live', initialCapital?: number) {
    const res = await fetch(`${API_BASE}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, initial_capital: initialCapital || 10000 })
    });
    if (!res.ok) throw new Error('Failed to start trading');
    return res.json();
  },

  async stopTrading() {
    const res = await fetch(`${API_BASE}/stop`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to stop trading');
    return res.json();
  },

  async emergencyFlatten() {
    const res = await fetch(`${API_BASE}/emergency-flatten`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to flatten position');
    return res.json();
  },

  async runBacktest(params: {
    start_date: string;
    end_date?: string;
    initial_capital?: number;
    buy_threshold_pct?: number;
    sell_threshold_pct?: number;
    adaptive_thresholds?: boolean;
  }): Promise<BacktestResult> {
    const res = await fetch(`${API_BASE}/backtest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    if (!res.ok) throw new Error('Failed to run backtest');
    return res.json();
  },

  async healthCheck(): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/healthz`);
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  }
};

// WebSocket for real-time updates
export function createWebSocket(onMessage: (data: TradingStatus) => void): WebSocket {
  const ws = new WebSocket(`ws://localhost:8000/ws`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  return ws;
}
