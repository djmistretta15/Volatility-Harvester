import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { formatCurrency, formatTime } from '../utils/format';

interface EquityChartProps {
  data: Array<{ timestamp: string; equity: number; drawdown?: number }>;
  height?: number;
}

export function EquityChart({ data, height = 350 }: EquityChartProps) {
  // Calculate prediction (simple moving average extrapolation)
  const prediction = data.length > 5 ? calculatePrediction(data) : [];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Equity Curve</h3>
        <p className="text-sm text-gray-500">Real-time portfolio value with trend prediction</p>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={[...data, ...prediction]} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorPrediction" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2}/>
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(time) => new Date(time).toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'})}
            stroke="#9ca3af"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
            stroke="#9ca3af"
            style={{ fontSize: '12px' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '12px'
            }}
            labelFormatter={(time) => formatTime(time)}
            formatter={(value: number) => [formatCurrency(value), 'Equity']}
          />
          <Area
            type="monotone"
            dataKey="equity"
            stroke="#0ea5e9"
            strokeWidth={2}
            fill="url(#colorEquity)"
            isAnimationActive={true}
            animationDuration={500}
          />
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="#f59e0b"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
            isAnimationActive={true}
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="mt-4 flex items-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-primary-500"></div>
          <span className="text-gray-600">Actual</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-warning-500" style={{ width: '20px' }}></div>
          <span className="text-gray-600">Predicted Trend</span>
        </div>
      </div>
    </div>
  );
}

function calculatePrediction(data: Array<{ timestamp: string; equity: number }>) {
  const recentData = data.slice(-10);
  const avgChange = recentData.reduce((sum, point, i) => {
    if (i === 0) return 0;
    return sum + (point.equity - recentData[i - 1].equity);
  }, 0) / (recentData.length - 1);

  const lastPoint = data[data.length - 1];
  const predictions = [];

  for (let i = 1; i <= 5; i++) {
    const futureTime = new Date(lastPoint.timestamp);
    futureTime.setMinutes(futureTime.getMinutes() + i * 5);

    predictions.push({
      timestamp: futureTime.toISOString(),
      predicted: lastPoint.equity + avgChange * i,
      equity: null // Don't show actual line
    });
  }

  return predictions;
}
