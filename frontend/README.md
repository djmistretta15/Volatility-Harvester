# Volatility Harvester Dashboard

Beautiful, real-time trading dashboard for the Volatility Harvester BTC trading engine.

## Features

- 📊 **Real-time Metrics** - Live equity, P&L, win rate, drawdown
- 📈 **Equity Chart** - Beautiful area chart with trend predictions
- 💹 **Live Trade Feed** - See every trade as it happens
- 🛡️ **Risk Monitor** - Circuit breaker status and health indicators
- ⚡ **Quick Controls** - Start/stop trading with one click
- 🎨 **Modern UI** - Clean, professional design with smooth animations
- 📱 **Responsive** - Works on desktop, tablet, and mobile

## Technology Stack

- **React 18** - Modern UI library
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Recharts** - Beautiful, responsive charts
- **Vite** - Lightning-fast build tool
- **Lucide Icons** - Clean, modern icons

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Open http://localhost:3000
```

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

### Docker

```bash
# Run with Docker (from project root)
make up

# Dashboard will be at http://localhost:3000
```

## Dashboard Sections

### Header
- **Status Indicator** - Shows if trading is active, paused, or stopped
- **System Health** - API, data, and trading status

### Metrics Cards
- **Total Equity** - Current portfolio value with P&L percentage
- **Realized P&L** - Profits/losses from closed positions
- **Win Rate** - Percentage of winning trades with visual progress bar
- **Max Drawdown** - Current drawdown with color-coded alerts

### Equity Chart
- Real-time portfolio value
- Trend prediction (5-period moving average extrapolation)
- Smooth animations and interactive tooltips
- Responsive design

### Risk Dashboard
- Circuit breaker status indicators
- Drawdown meter with color-coded warnings
- Win rate visualization
- System health checks

### Position Monitor
- Current state (FLAT/LONG/PAUSED)
- Cash and BTC holdings
- Unrealized P&L

### Live Trade Feed
- Recent trades with buy/sell indicators
- P&L for each trade
- Maker/taker fee indicators
- Trade statistics summary

### Control Panel
- Start Paper Trading button
- Start Live Trading button (with confirmation)
- Stop Trading button
- Emergency Flatten button (when in position)

## Color Scheme

- **Primary** - Blue (#0ea5e9) - Main actions and active states
- **Success** - Green (#22c55e) - Positive values, buy signals
- **Danger** - Red (#ef4444) - Negative values, sell signals, warnings
- **Warning** - Orange (#f59e0b) - Alerts, predictions
- **Gray** - Neutral backgrounds and text

## API Integration

The dashboard communicates with the backend API:

- **GET /status** - Polling every 2 seconds for real-time updates
- **GET /config** - Fetch trading configuration
- **POST /start** - Start paper or live trading
- **POST /stop** - Stop trading
- **POST /emergency-flatten** - Emergency position exit

## Responsive Design

The dashboard adapts to all screen sizes:

- **Desktop** (> 1024px) - Full 2-3 column layout
- **Tablet** (768px - 1024px) - 2 column layout
- **Mobile** (< 768px) - Single column stacked layout

## Accessibility

- Semantic HTML structure
- ARIA labels for interactive elements
- Keyboard navigation support
- Color contrast meets WCAG AA standards

## Browser Support

- Chrome/Edge (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)

## Development

### File Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.tsx       # Main dashboard component
│   │   ├── MetricCard.tsx      # Reusable metric card
│   │   ├── EquityChart.tsx     # Chart component
│   │   ├── TradeFeed.tsx       # Trade feed
│   │   ├── RiskDashboard.tsx   # Risk monitoring
│   │   ├── ControlPanel.tsx    # Trading controls
│   │   └── StatusIndicator.tsx # Status badge
│   ├── services/
│   │   └── api.ts              # API client
│   ├── types/
│   │   └── index.ts            # TypeScript types
│   ├── utils/
│   │   └── format.ts           # Formatting utilities
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── vite.config.ts
├── tailwind.config.js
└── package.json
```

### Adding New Features

1. Create component in `src/components/`
2. Define types in `src/types/`
3. Add API methods in `src/services/api.ts`
4. Integrate into Dashboard
5. Test responsiveness

### Styling

Uses Tailwind CSS utility classes:

```tsx
<div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
  <h3 className="text-lg font-semibold text-gray-900">Title</h3>
</div>
```

## Performance

- Components use React hooks for efficient updates
- Charts are memoized to prevent unnecessary re-renders
- Polling interval is 2 seconds (configurable)
- Production build is optimized and minified

## Future Enhancements

- [ ] WebSocket support for true real-time updates
- [ ] Historical chart with zoom/pan
- [ ] Trade history export (CSV)
- [ ] Custom alerts and notifications
- [ ] Parameter optimization tool
- [ ] Multi-strategy dashboard
- [ ] Dark mode toggle

## License

MIT - See main project LICENSE

---

Built with ❤️ for systematic traders
