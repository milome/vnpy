# Multi-Timeframe K-Line Chart Web Application

A quantitative trading research tool for visualizing multiple timeframe candlestick charts simultaneously.

## Features

- **Multi-Timeframe Display**: View 4H, 1H, 5M, and 1M candlestick charts on a single view
- **Visual Hierarchy**: Line thickness decreases for smaller timeframes
- **Transparency**: Bearish candles have transparency to show underlying smaller timeframes
- **Interactive**: Zoom, pan, and drawing tools
- **Real-time Ready**: WebSocket interface prepared for vnpy integration

## Tech Stack

- **Frontend**: React 18 + TypeScript
- **Build Tool**: Vite
- **Charting**: ECharts
- **Testing**: Vitest + Testing Library
- **Data Source**: CSV files (MHImain contract from HKFE)

## Project Structure

```
frontend/
├── src/
│   ├── components/     # React components
│   ├── services/       # Data loading and API services
│   ├── types/          # TypeScript type definitions
│   ├── utils/          # Utility functions
│   ├── tests/          # Test files
│   ├── App.tsx         # Main app component
│   ├── main.tsx        # Entry point
│   └── index.css       # Global styles
├── public/             # Static assets
└── package.json        # Dependencies
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Testing

```bash
# Run tests
npm test

# Run tests with UI
npm run test:ui
```

### Build

```bash
npm run build
```

## Data Format

CSV files are located in the `../data` directory with the following structure:

```csv
symbol,exchange,datetime,open,high,low,close,volume,turnover,open_interest
MHImain,HKFE,2017-11-14 00:00:00,29139.0,29142.0,29139.0,29142.0,4.0,116562.0,0.0
```

## Development Roadmap

- [x] Phase 1: Project Setup
- [ ] Phase 2: Data Layer Implementation
- [ ] Phase 3: Chart Visualization Core
- [ ] Phase 4: Interactive Features
- [ ] Phase 5: UI/UX Polish
- [ ] Phase 6: WebSocket Integration

## License

Private project for quantitative trading research.
