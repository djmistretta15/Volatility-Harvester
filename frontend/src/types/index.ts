export interface TradingStatus {
  running: boolean;
  state: 'flat' | 'long' | 'paused';
  paused: boolean;
  pause_reason: string | null;
  equity: number;
  cash: number;
  btc: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_trades: number;
  win_rate: number;
  drawdown_pct: number;
}

export interface Trade {
  timestamp: string;
  side: 'buy' | 'sell';
  qty: number;
  price: number;
  fee: number;
  is_maker: boolean;
  pnl?: number;
  reason: string;
}

export interface BacktestResult {
  initial_capital: number;
  final_capital: number;
  total_pnl: number;
  total_pnl_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  cagr: number;
  total_fees_paid: number;
  exposure_pct: number;
  trades: Trade[];
}

export interface Config {
  exchange: string;
  symbol: string;
  mode: 'backtest' | 'paper' | 'live';
  buy_threshold_pct: number;
  sell_threshold_pct: number;
  adaptive_thresholds: boolean;
  max_drawdown_pct: number;
  max_consecutive_losses: number;
  maker_first: boolean;
  reserve_pct: number;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
  drawdown?: number;
}
