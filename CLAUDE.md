# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a real-time cryptocurrency arbitrage detection system built for HackTheBurgh 2025. It monitors multiple exchange WebSockets simultaneously, detects price differences across exchanges, and uses ML to predict future spreads. The system includes a live Plotly Dash dashboard for visualization.

## Common Commands

### Running the System
```bash
# Start the full system (WebSocket streams + ML + dashboard)
python main.py

# Access dashboard at http://localhost:8050
```

### Training Models
```bash
# Train on historical data (if available)
python train_historical.py

# Train on live captured data
python train_live_capture.py
```

### Analytics
```bash
# Run analytics dashboard (separate from main system)
python run_analytics.py
```

### Dependencies
```bash
# Install all requirements
pip install -r requirements.txt

# Key packages: websocket-client, pandas, scikit-learn, xgboost, plotly, dash
```

### Directory Setup
The system requires `logs/` and `models/` directories:
```bash
mkdir logs models
```

## Architecture Overview

### Data Flow
1. **WebSocket Layer** (`data_ingestion.py`):
   - `MultiExchangeAggregator` orchestrates multiple exchange clients
   - Each exchange client (Coinbase, Binance, Bitstamp) has auto-reconnect logic
   - Symbol normalization: `BTCUSDT` → `BTC-USD`, `btcusd` → `BTC-USD`

2. **Detection Layer** (`arbitrage_detector.py`):
   - `ArbitrageDetector` receives normalized `PriceData` via callback
   - Maintains circular buffer (deque) of recent prices per symbol
   - Compares all exchange pairs in real-time
   - Accounts for exchange fees (taker fees: Coinbase 0.6%, Binance 0.1%, Bitstamp 0.5%)

3. **ML Layer** (`ml_predictor.py`):
   - `SpreadPredictor` uses Gradient Boosting to forecast spreads
   - Features: price changes, moving averages, volatility, bid-ask spread, volume
   - Auto-retrains every 5 minutes on accumulated data

4. **Visualization Layer** (`dashboard.py`):
   - Plotly Dash web app running in separate thread
   - Polls detector every 1 second for updates
   - Shows live price charts, opportunity table, spread heatmap, ML predictions

### Key Classes and Their Responsibilities

**PriceData** (config.py): Normalized price update from any exchange
- Handles timestamp conversion (unix ms → datetime with timezone)
- Fields: exchange, symbol, price, volume, bid, ask, timestamp

**ArbitrageOpportunity** (config.py): Detected profitable trade
- Contains buy/sell exchanges, prices, spread %, profit after fees
- Serializable to dict for JSON/dashboard

**ArbitrageDetector** (arbitrage_detector.py):
- `update_price()`: Called for each incoming price update
- `_check_arbitrage()`: Compares all exchange pairs for a symbol
- `_analyze_pair()`: Calculates spread and profit after fees
- Uses bid/ask prices when available, falls back to mid price
- Filters stale data (MAX_SPREAD_AGE_SECONDS = 5)

**SpreadPredictor** (ml_predictor.py):
- `engineer_features()`: Creates features per exchange, merges on timestamp
- `train()`: Trains Gradient Boosting model on historical data
- `predict_spread()`: Forecasts future spread between two exchanges
- Saves/loads models with joblib

**MultiExchangeAggregator** (data_ingestion.py):
- Manages concurrent WebSocket connections
- Each client runs in async task with exponential backoff retry
- Normalizes exchange-specific messages to PriceData

### Threading Model
- **Main thread**: asyncio event loop
  - WebSocket connections (async tasks)
  - ML training loop (async, every 5 min)
- **Dashboard thread**: Flask/Dash server (daemon thread)
  - Runs independently, polls detector for updates

## Configuration (config.py)

### Key Constants
- `MIN_PROFIT_THRESHOLD`: Minimum profit % after fees to flag opportunity (default 0.2%)
- `MAX_SPREAD_AGE_SECONDS`: Discard prices older than this (default 5s)
- `DATA_BUFFER_SIZE`: Number of historical prices to keep per symbol (default 10000)

### Exchange Configuration
Edit `EXCHANGE_CONFIGS` to modify:
- WebSocket URLs
- Fee percentages
- Monitored symbols

### Symbol Normalization
`SYMBOL_MAPPINGS` dict handles exchange-specific formats:
- Binance uses `BTCUSDT`
- Bitstamp uses `btcusd`
- Coinbase uses `BTC-USD` (standard format)

## Development Patterns

### Adding a New Exchange
1. Create new client class in `data_ingestion.py` inheriting from `BaseExchangeClient`
2. Implement `connect()` and `_parse_message()` methods
3. Add exchange to `Exchange` enum in `config.py`
4. Add `ExchangeConfig` entry with WebSocket URL and fee structure
5. Add symbol mappings to `SYMBOL_MAPPINGS`
6. Register in `MultiExchangeAggregator.__init__()`

### Modifying ML Features
Features are engineered per-exchange in `SpreadPredictor.engineer_features()`:
- Each exchange gets: price, price_change, moving averages, volatility, bid-ask spread, volume
- Features are prefixed with exchange name: `Coinbase_price`, `Binance_price`, etc.
- All exchange features are merged on timestamp
- Missing values are forward-filled

### Dashboard Customization
Dashboard components in `dashboard.py` use Dash callbacks:
- Each component has `@app.callback` decorator
- Input: `dcc.Interval` component triggers updates every 1000ms
- Output: Updated HTML/chart components
- Callbacks fetch fresh data from `self.detector` and `self.ml_predictor`

## File Structure

### Core Modules
- `main.py`: Entry point, orchestrates all components
- `config.py`: Data models (PriceData, ArbitrageOpportunity), exchange configs, constants
- `data_ingestion.py`: WebSocket clients for exchanges
- `arbitrage_detector.py`: Core detection logic and opportunity storage
- `ml_predictor.py`: Machine learning models for spread prediction
- `dashboard.py`: Plotly Dash web dashboard

### Training Scripts
- `train_historical.py`: Train ML model on historical data
- `train_live_capture.py`: Capture live data and train model
- `historical_data.py`: Historical data fetching utilities

### Documentation
- `README.md`: Main project documentation
- `ARCHITECTURE.md`: Deep technical architecture details
- `QUICK_START.md`: Step-by-step setup and demo guide
- Various training guides (HISTORICAL_TRAINING_GUIDE.md, LIVE_TRAINING_GUIDE.md)

### Generated Artifacts
- `logs/`: Application logs (arbitrage_{time}.log)
- `models/`: Trained ML models (.pkl files)

## Error Handling

### WebSocket Disconnections
All exchange clients implement exponential backoff:
- Retry count tracks consecutive failures
- Backoff: 2^retry_count seconds (1s, 2s, 4s, 8s, 16s)
- Max 5 retries before giving up

### Invalid Data
Price parsing is wrapped in try/except:
- Log warning on invalid message format
- Skip message and continue (don't crash)

### ML Training Failures
Training errors are caught and logged:
- System continues with previous model
- Won't crash if training fails

## Performance Characteristics

### Latency
- WebSocket receive: ~20ms
- Arbitrage detection: <1ms (in-memory comparison)
- End-to-end (price update → opportunity detected): ~70ms

### Throughput
- Processes ~10,000 messages/second from 3 exchanges × 3 symbols
- Dashboard updates at 1 Hz (1-second intervals)

### Memory
- Price buffer: ~2.4 MB (1000 items × 3 symbols)
- ML model: ~5 MB
- Total: ~10 MB (very efficient)

## Testing Approach

### Manual Testing
Run system and verify:
- All 3 exchanges connect (check terminal logs)
- First opportunity appears within 30 seconds
- Dashboard updates in real-time
- ML predictions appear after 5+ minutes

### Expected Metrics (10 min run)
- Total opportunities: 50-80
- Average profit: 0.65-0.85% after fees
- Max profit: 1.5-3.0%

## Common Issues

### No Opportunities Detected
- Normal in low volatility periods
- Lower `MIN_PROFIT_THRESHOLD` in config.py
- Check all exchanges are connected (terminal logs)

### Dashboard Not Loading
- Ensure port 8050 is available
- Try http://127.0.0.1:8050 instead of localhost
- Check browser console for errors

### WebSocket Connection Errors
- Check internet connection
- Some exchanges may have rate limits
- System will auto-retry with backoff

### ML Model Not Training
- Requires 5+ minutes of data collection
- Minimum 100 data points needed
- Check logs/ directory for error messages