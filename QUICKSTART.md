# Quick Start Guide

## 🚀 Getting Started with the Finance Application

### Installation (One-time setup)

```bash
# Navigate to project directory
cd "E:\Progs\EGX ToolKit"

# Install required packages
pip install -r requirements.txt
```

### Running the Application

#### Option 1: Command Line Interface (CLI)

```bash
python app.py --limit 5 --days 90
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

---

## 📊 Available Trading Strategies

1. **Swing Trading** - EMA crossover with RSI confirmation
2. **Position Trading** - Long-term support/resistance via 200-day SMA
3. **Algorithmic (Mean Reversion)** - Bollinger Bands price reversions
4. **Price Action** - Engulfing candles and hammer patterns

---

## 🔧 Customization

### Modify Configuration

Edit `config.py` to customize:

```python
# Change technical indicators
EMA_SHORT = 20  # Change from 20
EMA_LONG = 50   # Change from 50
SMA_LONG = 200

# Adjust signal sensitivity
MIN_SIGNAL_COUNT = 3  # For "Golden List"
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
```

### Run Analysis on Different Stocks

```bash
python app.py --symbols COMI,EHDR,ABUK --days 365
```

### Use Real Data Source

To use real TradingView data:

```bash
python app.py --data-source tv
```

If `tvDatafeed` fails or you don’t have access, the app falls back to cached data.

---

## 📁 Project Structure

```
EGX ToolKit/
├── app.py               # Main entry point (CLI)
├── dashboard.py         # Streamlit web dashboard
├── config.py            # Configuration & EGX symbols list
├── database.py          # DuckDB operations
├── data_fetcher.py      # Data fetching
├── strategies.py        # Trading strategy implementations
├── analysis.py          # Signal aggregation & analysis
├── requirements.txt     # Python dependencies
├── README.md            # Full documentation
└── data/
    └── stocks.duckdb    # Local database (created at runtime)
```

---

## 🗄️ Database

The application uses **DuckDB** for fast, analytical database operations:

- **Location**: `data/stocks.duckdb`
- **Auto-created**: First run creates tables
- **Persistent**: Data saved between sessions
- **Fast queries**: SQL-optimized for analysis
Note: the CLI creates a stable snapshot at the end of each run for read-only usage.

### Tables

1. **stocks** - OHLCV price data
2. **indicators** - Calculated technical indicators
3. **signals** - Generated buy/sell signals with confidence

---

## ⚙️ Supported EGX Symbols

90+ Egyptian stocks including:
- Blue chips: ABUK, ADIB, ADCO, ASEC
- High liquidity: COMI, EHDR, EXPE
- Mid-cap: And 80+ more...

See `config.EGX_SYMBOLS` for complete list.

---

## 🐛 Troubleshooting

### "No modules named 'duckdb'"
```bash
pip install -r requirements.txt
```

### "No data available for symbol"
- Ensure TradingView data source is accessible
- Check symbol spelling (must be uppercase)

### "Read-only requires a snapshot"
- Run `python app.py` once to generate the first snapshot
- Then use `python app.py --read-only`

### Dashboard won't load
```bash
# Install/upgrade Streamlit
pip install --upgrade streamlit

# Run with verbose output
streamlit run dashboard.py --logger.level=debug
```

---

## 📈 Next Steps

1. **Run analysis**: `python app.py`
2. **View results**: Check the dashboard output
3. **Customize**: Edit strategies in `strategies.py`
4. **Integrate**: Use `app.FinanceApp` class in your own code
5. **Deploy**: Run `dashboard.py` with Streamlit cloud

---

## 💡 Tips

- Test strategies on **historical data** first
- Monitor **confidence levels** (0.0-1.0 scale)
- Use **golden list** for highest-conviction setups
- Review **market memo** for overall direction

---

## 📞 Support

See `README.md` for full API documentation and advanced usage.

Refer to `AppPlan.md` for architecture and design details.
