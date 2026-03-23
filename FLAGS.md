# CLI Flags Reference

This project’s CLI flags are available when running:

```bash
python app.py [flags]
```

If you use Streamlit:

```bash
streamlit run app.py
```

then the CLI flags are **not** applied, and the Streamlit UI loads instead.

## Flags

`--read-only`
Open the database in read-only mode. Uses the latest snapshot/backup and never writes.
If a writer is active, it will continue reading historical data until the next snapshot is ready.

Note: If no snapshot exists, `--read-only` will wait for the writer to finish and create one.
If no writer is running, it will run the pipeline once to create a snapshot, then exit.

`--backup-db`
Create a timestamped backup of the live DuckDB file before running the pipeline.

`--data-source {tv|mock}`
Select data source. Default: `tv`.

- `tv`: TradingView via `tvDatafeed`. If it fails (e.g., no internet), the app falls back to cached historical data from DuckDB.
 - `mock`: Synthetic data for testing only (stored in `data/stocks_mock.duckdb` and purged after the run).

`--symbols SYMBOL1,SYMBOL2`
Comma-separated list of symbols to analyze. Overrides `--limit`.

`--limit N`
Analyze only the first `N` symbols from `EGX_SYMBOLS`.

`--days N`
Number of days of data to fetch/analyze. Default: `365`.

`--allow-unknown-symbols`
Allow symbols not in `EGX_SYMBOLS` when using `--symbols`.

`--purge-symbols`
Delete existing data for each symbol before loading new data.

`--purge-future-rows`
Delete any rows with dates after today before running.

`--sync-symbols-tv`
Sync EGX symbols from TradingView (via `tradingview-screener`), remove dormant symbols, compare with config, and update the cached list used by `config.py`.

`--list-symbols`
List all tradeable EGX symbols (from cached list if present, otherwise fallback list) and exit.

`--latest-table`
Print latest data table (High, Low, Close, Buy/Sell, Strategies, Confidence, Advice) and exit.

`--export-csv [PATH]`
Export the latest table to CSV. If PATH is omitted, writes `Untitled.csv` in the current directory.

`--export-excel [PATH]`
Export the latest table to Excel (.xlsx). If PATH is omitted, writes `Untitled.xlsx` in the current directory.

`--export-pdf [PATH]`
Export the latest table to PDF (requires `reportlab`). If PATH is omitted, writes `Untitled.pdf` in the current directory.

## Examples

Fetch real data for a few symbols:

```bash
python app.py --data-source tv --symbols ADIB,ALUM --days 250
```

Quick test with a small subset:

```bash
python app.py --limit 3 --days 30
```

Sync symbol list from TradingView and update cache:

```bash
python app.py --sync-symbols-tv
```
`--purge-mock-after`
Delete the mock database file after the run (mock data source only).  
Note: mock runs auto-purge even without this flag.

`--update`
Update the CLI to the latest version from the git repo and exit.