# Finance Application - Project Index

## 📚 Documentation Files (Read These First)

1. **QUICKSTART.md** - Short Guide
   - Installation in 2 minutes
   - Run CLI or Streamlit dashboard
   - Customization examples
   - Troubleshooting tips

2. **README.md** - Full Reference & Quick Start
   - Complete API documentation
   - Installation instructions
   - Run CLI or Streamlit dashboard
   - Database schema details
   - Development guide
   - All supported features

3. **PROJECT_SUMMARY.md** - What Was Built
   - Phase-by-phase implementation details
   - Architecture overview
   - Feature list
   - Verification results

4. **AppPlan.md** - Original Requirements
   - Business requirements
   - Strategy specifications
   - Implementation approach

5. **FLAGS.md** - CLI Flags Reference
   - All supported flags
   - Examples and usage notes

---

## 🔧 Application Files

### Core Engine
- **config.py** - Settings, symbols, technical parameters
- **database.py** - DuckDB operations
- **data_fetcher.py** - Data source abstraction
- **strategies.py** - Trading strategy implementations
- **analysis.py** - Signal aggregation & analysis
- **symbol_sync.py** - TradingView symbol sync & comparison

### User Interfaces
- **app.py** - CLI application (run with: `python app.py`)
- **dashboard.py** - Streamlit web UI (run with: `streamlit run dashboard.py`)

### Configuration
- **requirements.txt** - Python dependencies
### Utilities
- **scripts/update_egx_symbols.py** - Update symbols from EGX list source

---

## 🚀 Quick Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run CLI version (TV data by default)
python app.py

# Limit to a few symbols for testing
python app.py --symbols ADIB,ALUM --days 250

# List tradeable symbols
python app.py --list-symbols

# Sync symbols from TradingView (removes dormant)
python app.py --sync-symbols-tv

# Run web dashboard
streamlit run dashboard.py

# Streamlit entrypoint shortcut
streamlit run app.py

# Verify installation
python -c "from database import StockDatabase; print('✓ Ready to use!')"
```

---

## 📊 What This Project Does

Analyzes Egyptian stocks using multiple trading strategies:
- Generates buy/sell signals with confidence scores
- Identifies high-probability setups ("Golden List")
- Calculates market sentiment
- Provides actionable recommendations
- Stores data in a persistent DuckDB database
- Supports TradingView data with cached fallback
- Keeps mock data isolated and auto-purged

---

## 🎯 Trading Strategies Included

| Strategy | Logic | Best For |
|----------|-------|----------|
| **Swing Trading** | EMA crossovers + RSI | Trend-following 2-4 week trades |
| **Position Trading** | 200-day SMA tracking | Long-term (6+ month) holdings |
| **Mean Reversion** | Bollinger Bands | Counter-trend fades |
| **Price Action** | Candle patterns | Confirmation of support/resistance |

---

## 📈 Key Features

✅ **Persistent Database** - DuckDB stores everything locally
✅ **Auto-Sync** - Loads only new data, skips existing records
✅ **Multi-Strategy** - Compare different approaches simultaneously
✅ **Confidence Scoring** - Know how reliable each signal is
✅ **Market Sentiment** - Overall bullish/bearish gauge
✅ **Golden List** - Stocks with 3+ strategy confirmations
✅ **Web Dashboard** - Real-time visualization
✅ **Mock Data** - Only when explicitly requested
✅ **Symbol Sync** - Update tradable symbols from TradingView

---

## 🗂️ Project Structure

```
FINance/
├── QUICKSTART.md           ← Start here!
├── README.md               ← Full documentation
├── PROJECT_SUMMARY.md      ← What was built
├── INDEX.md                ← This file
│
├── config.py               ← Settings & symbols
├── database.py             ← DuckDB layer
├── data_fetcher.py         ← Data sources
├── strategies.py           ← Strategy implementations
├── analysis.py             ← Signal aggregation
├── app.py                  ← CLI entry point
├── dashboard.py            ← Streamlit UI
│
├── requirements.txt        ← Dependencies
├── AppPlan.md              ← Original specs
├── FLAGS.md                ← CLI flags
├── symbol_sync.py           ← TradingView symbol sync
├── scripts/
│   └── update_egx_symbols.py← EGX symbols importer
│
└── data/
    ├── stocks.duckdb        ← Database (auto-created)
    ├── stocks_mock.duckdb   ← Mock DB (auto-purged)
    └── egx_symbols.csv      ← Cached symbol list
```

---

## 🎓 How to Use

### 1. As a Standalone Tool
```bash
python app.py --symbols COMI,ABUK --days 250
```
Analyzes the selected symbols and displays results in console.

### 2. As a Web Dashboard
```bash
streamlit run dashboard.py
```
Opens interactive web interface with real-time metrics.

### 3. In Your Own Code
```python
from app import FinanceApp

app = FinanceApp()
app.run_analysis_pipeline(symbols=['COMI', 'ABUK'])
app.display_dashboard()
```

### 4. Extend with New Strategies
See README.md "Development Guide" section.

---

## 🔌 Integration Examples

### Get Market Sentiment
```python
from database import StockDatabase
from analysis import AnalysisEngine

db = StockDatabase()
engine = AnalysisEngine(db)
sentiment = engine.get_market_sentiment()
print(f"Market is {sentiment}% bullish")
```

### Find High-Conviction Stocks
```python
golden_list = engine.get_golden_list(min_signals=3)
for symbol, count in golden_list:
    print(f"{symbol}: {count} strategy signals")
```

### Run Custom Analysis
```python
from strategies import SwingTradingStrategy
strategy = SwingTradingStrategy(data_df)
signals = strategy.generate_signals()
```

---

## ⚙️ Configuration

All settings in **config.py**:

```python
# Technical indicators
EMA_SHORT = 20          # 20-period EMA
EMA_LONG = 50           # 50-period EMA
SMA_LONG = 200          # 200-period SMA
RSI_PERIOD = 14         # RSI lookback
BB_PERIOD = 20          # Bollinger Bands period
BB_STD_DEV = 2          # Standard deviations

# Signal criteria
MIN_SIGNAL_COUNT = 3    # For "Golden List"
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
```

Symbol lists are loaded from `data/egx_symbols.csv` when present.  
Run `python app.py --sync-symbols-tv` to refresh the list from TradingView.

---

## 📞 Support Resources

- **Quick questions?** → See QUICKSTART.md
- **Need API docs?** → See README.md
- **How was it built?** → See PROJECT_SUMMARY.md
- **Original requirements?** → See AppPlan.md
- **Code issues?** → Check docstrings in source files

---

## ✅ Verification Checklist

- [x] Database schema created
- [x] Strategies implemented (Swing, Position, Mean Reversion, Price Action)
- [x] Signal generation working
- [x] CLI and web interfaces ready
- [x] TradingView integration supported
- [x] Mock data isolated and auto-purged
- [x] Symbol sync and validation supported

---

## 🎉 Ready to Go!

**Next Step:** Open `QUICKSTART.md` and follow the installation steps.

The Finance Application is fully functional and ready for:
- Stock analysis and trading signal generation
- Strategy backtesting and development
- Real-time dashboard monitoring
- Integration with trading systems or bots

---

**Last Updated:** March 16, 2026
**Status:** ✅ Active Development
