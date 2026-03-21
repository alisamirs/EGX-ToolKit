# Finance Application - EGX Trading Strategy Analysis System

## Overview

A comprehensive Python-based trading strategy analysis system for Egyptian Stock Exchange (EGX) stocks. Uses DuckDB for persistent data storage, multiple technical analysis strategies, and automated signal generation.

## Project Structure

```
EGX ToolKit/
├── config.py              # Configuration and constants
├── database.py            # DuckDB operations and data persistence
├── data_fetcher.py        # Data fetching from external sources
├── strategies.py          # Trading strategy implementations
├── analysis.py            # Signal aggregation and market analysis
├── app.py                 # Main CLI application
├── dashboard.py           # Streamlit web dashboard
├── requirements.txt       # Python dependencies
└── data/                  # Data directory (created at runtime)
    └── stocks.duckdb      # Local DuckDB database file
```

## Features

### Phase 1: Core Architecture
- **Database Engine**: DuckDB for persistent, analytical storage
- **Auto-Load Logic**: Syncs missing data on launch
- **Modular Design**: Clean separation of concerns

### Phase 2: Trading Strategies

| Strategy | Logic | Recommendation |
|----------|-------|-----------------|
| **Swing Trading** | 20/50 EMA Cross + RSI | Buy on bullish cross |
| **Position Trading** | 200-day SMA tracking | Long-term value plays |
| **Algorithmic (Mean Reversion)** | Bollinger Bands | Buy at lower band |
| **Price Action** | Engulfing/Hammer patterns | Chart pattern signals |
| **Day Trading** | Intraday VWAP analysis | Pre-close exits |
| **Scalping** | 1-5 min micro trends | High-liquidity stocks |

### Phase 3: Technical Implementation
- **Modularity**: Each strategy is an independent class
- **Data Handling**: Pandas for efficient data transformation
- **DuckDB Integration**: SQL-based data access layer
- **Data Source Abstraction**: Easy switching between data sources

### Phase 4: Dashboard & Recommendations
- **Market Sentiment**: Bullish/bearish gauge
- **Golden List**: Stocks with 3+ simultaneous signals
- **Strategy-Specific Advice**: Tailored recommendations
- **Daily Market Memo**: Overall market assessment

## Installation

### Requirements
- Python 3.9+
- DuckDB 1.1.3+
- Pandas 2.1.4+
Note: `reportlab` is required for PDF export and `openpyxl` is required for Excel export.

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Or run the Streamlit dashboard
streamlit run dashboard.py
```

## Configuration

Edit `config.py` to customize:

```python
# Technical indicators
EMA_SHORT = 20
EMA_LONG = 50
SMA_LONG = 200
RSI_PERIOD = 14
BB_PERIOD = 20
BB_STD_DEV = 2

# Market hours (Egypt local time)
MARKET_OPEN = "10:00"
MARKET_CLOSE = "14:30"

# Signal thresholds
MIN_SIGNAL_COUNT = 3  # For "Golden List"
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
```

## Usage

### CLI Application

```python
from app import FinanceApp

# Initialize
app = FinanceApp()

# Run analysis on specific symbols
app.run_analysis_pipeline(symbols=['COMI', 'ABUK', 'EHDR'], days=365)

# Display dashboard
app.display_dashboard()

# Clean up
app.close()
```

### Streamlit Dashboard

```bash
streamlit run dashboard.py
```

Features:
- Real-time market sentiment
- Golden list visualization
- High-confidence signal display
- Market memo and recommendations

## Data Flow

1. **Data Loading**: Fetches stock data from TradingView only
2. **Persistence**: Stores in local DuckDB database
3. **Indicator Calculation**: Computes EMA, SMA, RSI, Bollinger Bands
4. **Signal Generation**: Each strategy generates BUY/SELL signals
5. **Aggregation**: Combines signals across strategies
6. **Analysis**: Identifies high-probability setups
7. **Dashboard**: Displays recommendations and sentiment

## Read-Only Mode & Snapshots

The toolkit uses a single-writer pattern. When the writer finishes a run, it writes a stable snapshot database:

```
data/stocks.duckdb.snapshot
```

`--read-only` always opens the latest snapshot/backup and never touches the live DB.  
If the writer is running, readers continue using the last completed snapshot.

If no snapshot exists yet, `--read-only` will:
1. Wait for a writer to finish and create one, or
2. If no writer is running, it will run the pipeline once to create the snapshot, then exit.

## CLI Flags

Run:

```bash
python app.py --help
```

Or see `FLAGS.md` for the full list of supported flags and examples.

## Database Schema

### stocks
```sql
CREATE TABLE stocks (
    symbol VARCHAR,
    date DATE,
    open DECIMAL(10, 4),
    high DECIMAL(10, 4),
    low DECIMAL(10, 4),
    close DECIMAL(10, 4),
    volume BIGINT,
    PRIMARY KEY (symbol, date)
);
```

### indicators
```sql
CREATE TABLE indicators (
    symbol VARCHAR,
    date DATE,
    ema_20, ema_50, sma_200, rsi, bb_upper, bb_middle, bb_lower, vwap DECIMAL,
    PRIMARY KEY (symbol, date)
);
```

### signals
```sql
CREATE TABLE signals (
    symbol VARCHAR,
    date DATE,
    strategy VARCHAR,
    signal VARCHAR,
    confidence DECIMAL(3, 2),
    PRIMARY KEY (symbol, date, strategy)
);
```

## Development Guide

### Adding a New Strategy

1. Create a new class inheriting from `StrategyEngine`:

```python
from strategies import StrategyEngine

class MyStrategy(StrategyEngine):
    def generate_signals(self):
        # Your logic here
        signals = []
        # ... populate signals ...
        return signals
```

2. Register in `app.py`:

```python
strategies = {
    'My Strategy': MyStrategy(df),
    # ... other strategies ...
}
```

### Switching Data Sources

Edit `data_fetcher.py` to implement your own fetcher:

```python
class YourDataFetcher(DataFetcher):
    def fetch_symbol_data(self, symbol, days=365):
        # Your data fetching logic
        pass
```

## API Reference

### StockDatabase

```python
db = StockDatabase()
db.create_tables()
db.insert_stock_data(symbol, date, open, high, low, close, volume)
data = db.get_symbol_data(symbol, days)
latest_date = db.get_latest_date_for_symbol(symbol)
db.close()
```

### AnalysisEngine

```python
engine = AnalysisEngine(db)
sentiment = engine.get_market_sentiment(date)
golden_list = engine.get_golden_list(min_signals=3, date)
recommendations = engine.get_strategy_recommendations(date)
memo = engine.generate_market_memo(sentiment)
```

### StrategyEngine

```python
from strategies import SwingTradingStrategy
strategy = SwingTradingStrategy(dataframe)
signals = strategy.generate_signals()
# signals: List[dict] with keys: date, signal, confidence
```

## EGX Symbols Supported

200+ stocks including:
- COMI, ABUK, EHDR (High liquidity)
- ADIB, ADCO, ASEC (Blue chips)
- And many more...

See `config.EGX_SYMBOLS` for complete list.

## Performance Considerations

- **Database**: DuckDB is optimized for analytical queries
- **Caching**: Data is persisted to avoid redundant fetches
- **Scalability**: Efficient for 95+ stocks with 365+ days history
- **Memory**: Streamlined with pandas/numpy operations

## Future Enhancements

- [ ] Real-time data streaming
- [ ] Machine learning signal validation
- [ ] Portfolio optimization
- [ ] Risk management overlays
- [ ] Mobile app integration
- [ ] Email/SMS notifications

## License

Proprietary - Trading System

## Support

For issues or questions, refer to AppPlan.md for architecture details.
