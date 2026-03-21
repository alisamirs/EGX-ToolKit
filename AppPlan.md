# Comprehensive development plan.

---

## Phase 1: The Core Architecture (DuckDB + Python)

DuckDB will act as your "Local Analytical Warehouse." Instead of reloading CSVs every time, the app will store data in a persistent `.duckdb` file.

* **Database Engine:** DuckDB (Persistent storage).
* **Data Source:** `tvDatafeed` or `tradingview-screener` (fetching `.EGX` symbols).
* **Visualization:** `Plotly` (for interactive candle charts) or `Streamlit` (for the app UI).

### The "Auto-Load" Logic

Every time the app launches, it should:

1. **Check Local DB:** See if the latest data is already in `stocks.duckdb`.
2. **Sync:** Download only the "missing" days from TradingView and append them to the DuckDB table.
3. **Analyze:** Run the strategy SQL queries directly on the DB.

---

## Phase 2: Implementing the Trading Strategies

You will build an "Analysis Engine" that processes your 95 stocks through these lenses:

| Strategy | Logic / Implementation | Recommendation Criteria |
| --- | --- | --- |
| **Swing Trading** | Uses **20/50 EMA Cross** + **RSI**. Looks for trends lasting weeks. | "Hold" if price is above 50 EMA; "Buy" on bullish cross. |
| **Position Trading** | Focused on **200-day SMA** and Macro trends. | Long-term "Value" play. Recommended for low-volatility blue chips. |
| **Day Trading** | Analyzes **Intraday VWAP** and Volume spikes. | High conviction; exit before EGX close (2:30 PM CLT). |
| **Price Action** | Detects **Engulfing Candles**, **Hammer** patterns, or Support/Resistance breaks. | Signal generated on specific "Chart Patterns" without indicators. |
| **Algorithmic** | A "Mean Reversion" bot using **Bollinger Bands**. | Automatic Buy when price hits Lower Band; Sell at Mean. |
| **Scalping** | Extreme short-term (1-5 min bars) looking for tiny spreads. | Only recommended for high-liquidity stocks (e.g., COMI, ABUK). |

---

## Phase 3: Technical Implementation Approach (Python)

This phase will focus on the architectural patterns and libraries used for implementing the strategies in Python.

*   **Modularity**: Each trading strategy will be implemented as a distinct, reusable module or class.
*   **Data Handling**: Utilize `pandas` for efficient data manipulation and transformation before ingestion into or after retrieval from DuckDB.
*   **DuckDB Integration**: Establish a clear data access layer for interacting with `stocks.duckdb`, ensuring efficient querying and data updates.
*   **Data Source Abstraction**: Create an abstraction layer for fetching data from `tvDatafeed` or `tradingview-screener` to facilitate easy switching or parallel use of data sources.


---

## Phase 4: App Launch Workflow & Recommendations

Every time you open the app, it should present a **Dashboard Summary**:

1. **Market Sentiment:** A "Fear/Greed" gauge based on the EGX index position.
2. **The "Golden List":** Stocks that triggered a signal in *more than three* strategies simultaneously.
3. **Strategy-Specific Advice:**
* *Scalpers:* "High volatility in EHDR; spread is narrow enough for 1% moves."
* *Position Traders:* "Approaching 200-day support; potential entry for 6-month hold."


4. **Overall Conclusion:** A daily "Market Memo" (e.g., "Market is sideways; favor Price Action over Trend Following today.")
