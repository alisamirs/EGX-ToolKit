# Finance Application - EGX Trading Strategy Analysis System

## Overview

A comprehensive Python-based trading strategy analysis system for Egyptian Stock Exchange (EGX) stocks. Uses DuckDB for persistent data storage, multiple technical analysis strategies, and automated signal generation.

## Project Structure

```
EGX ToolKit/
|-- config.py              # Configuration and constants
|-- database.py            # DuckDB operations and data persistence
|-- data_fetcher.py        # Data fetching from external sources
|-- strategies.py          # Trading strategy implementations
|-- analysis.py            # Signal aggregation and market analysis
|-- app.py                 # Main CLI application
|-- dashboard.py           # Streamlit web dashboard
|-- requirements.txt       # Python dependencies
`-- data/                  # Data directory (created at runtime)
    `-- stocks.duckdb      # Local DuckDB database file
```

## Installation

### Requirements
- Python 3.9+ (including 3.13)
- DuckDB 1.1.3+
- Pandas 2.1.4+
Note: `reportlab` is required for PDF export and `openpyxl` is required for Excel export.

### Setup

```bash
pip install git+https://github.com/alisamirs/EGX-ToolKit.git
egx-toolkit --help
```

If you want PDF export, install the optional dependency:

```bash
pip install "egx-toolkit[pdf]"
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

Data directory defaults to a per-user location:

- Windows: `%APPDATA%\\egx-toolkit`
- Linux: `~/.local/share/egx-toolkit`

Override with `EGX_DATA_DIR`.

## Usage & Quick Start

### Running the Application

#### Option 1: Command Line Interface (CLI)

```bash
egx-toolkit --limit 5 --days 90
```

**What it does:**
- Fetches data for 5 test symbols
- Runs all trading strategies
- Displays a market summary with:
  - Market sentiment percentage
  - Golden list (stocks with 3+ signal triggers)
  - Top high-confidence recommendations
  - Market memo

**Output example:**
```
Starting analysis pipeline...
[1/5] Processing ABUK...
  Found 332 signals
...
Analysis complete.

============================================================
          FINANCE DASHBOARD SUMMARY
============================================================
Market Sentiment: 50.0%
Market Memo: Market is slightly bearish...
🌟 GOLDEN LIST (3+ Strategy Signals):
  (Results will appear when available)
...
```

#### Option 2: Streamlit Web Dashboard

```bash
streamlit run dashboard.py
```

**Features:**
- Interactive web interface
- Real-time market sentiment gauge
- Golden list visualization
- Signal recommendations
- Market analysis

### CLI Application

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

## EGX Symbols Supported

200+ stocks including:
- COMI, ABUK, EHDR (High liquidity)
- ADIB, ADCO, ASEC (Blue chips)
- And many more...

See `EGX_SYMBOLS` in config.py for complete list.

## Future Enhancements

- [ ] Real-time data streaming
- [ ] Machine learning signal validation
- [ ] Portfolio optimization
- [ ] Risk management overlays
- [ ] Mobile app integration
- [ ] Email/SMS notifications

## Support

For issues or questions, refer to AppPlan.md for architecture details.
