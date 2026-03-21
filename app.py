"""Main application entry point."""

__version__ = "1.0.0"
__about__ = "EGX ToolKit - EGX Trading Strategy Analysis System"

from datetime import datetime
import argparse
import sys
import concurrent.futures
from pathlib import Path
import shutil
import os
from database import StockDatabase, WriterLock
from data_fetcher import MockDataFetcher, TVDataFeedFetcher, CachedDataFetcher
from strategies import (
    SwingTradingStrategy, PositionTradingStrategy,
    AlgorithmicMeanReversionStrategy, PriceActionStrategy
)
from analysis import AnalysisEngine, DashboardData
import pandas as pd
from config import EGX_SYMBOLS, EGX_INDEX_SYMBOL, DATA_DIR, DB_PATH
from symbol_sync import sync_symbols_from_tradingview


class FinanceApp:
    """Main application for stock analysis and trading signals."""
    
    def __init__(self, fetcher=None, fetcher_factory=None, purge_on_load=False, db_path=None, read_only=False):
        self.db = StockDatabase(db_path=db_path, read_only=read_only) if db_path else StockDatabase(read_only=read_only)
        if not self.db.read_only:
            self.db.create_tables()
        if fetcher:
            self.fetcher = fetcher
        elif fetcher_factory:
            self.fetcher = fetcher_factory(self.db)
        else:
            try:
                self.fetcher = TVDataFeedFetcher()
                print("Initialized TVDataFeedFetcher.")
            except (ImportError, Exception) as e:
                print(f"Could not initialize TVDataFeedFetcher ({e}). Falling back to cached historical data.")
                self.fetcher = CachedDataFetcher(db=self.db)
        self.analysis = AnalysisEngine(self.db)
        self.purge_on_load = purge_on_load
        self.last_symbols = None
        self._db_path = db_path
    
    def load_data(self, symbol, days=365, db=None):
        """Load stock data and check if sync is needed, fetching only new data if possible."""
        if db is None:
            db = self.db # Fallback to instance's db if not provided (e.g., when called from main thread)
        
        latest_local = db.get_latest_date_for_symbol(symbol)

        # If latest_local is in the future (likely bad/mock data), treat as stale.
        if latest_local and latest_local > datetime.now().date():
            print(f"  Detected future-dated data for {symbol} (latest: {latest_local}). Forcing refresh.")
            latest_local = None
        
        days_to_fetch = days
        if not self.purge_on_load and latest_local: # Only use latest_local for days_to_fetch if not purging
            time_difference = datetime.now().date() - latest_local
            if time_difference.days > 0:
                # Fetch data since the latest local date, plus a small buffer
                days_to_fetch = time_difference.days + 5 # Add buffer for weekends/holidays
                # Ensure we don't fetch more than the originally requested 'days' if 'latest_local' is very old
                days_to_fetch = min(days_to_fetch, days)
            else:
                # Data is up to date or future dated, no need to fetch
                print(f"  Data for {symbol} is up to date (latest: {latest_local}). Skipping fetch.")
                return pd.DataFrame() # Return empty DataFrame if no fetch is needed
        
        # Fetch data using the fetcher
        data = self.fetcher.fetch_symbol_data(symbol, days_to_fetch)
        
        if data is None or data.empty:
            print(f"  No new data fetched for {symbol}.")
            return pd.DataFrame() # Return empty DataFrame if no data fetched

        # If using TVDataFeed, remove any future rows beyond the latest fetched date
        if isinstance(self.fetcher, TVDataFeedFetcher):
            if 'datetime' in data.columns:
                max_date = pd.to_datetime(data['datetime']).max().date()
            else:
                max_date = pd.to_datetime(data.index).max().date()
            db.delete_symbol_data(symbol, date_after=max_date)

        if self.purge_on_load:
            db.delete_symbol_data(symbol)
        
        # Filter data to only include dates after latest_local, if applicable, UNLESS purging
        if latest_local and not self.purge_on_load:
            if 'datetime' in data.columns:
                data['datetime'] = pd.to_datetime(data['datetime']).dt.date
                data = data[data['datetime'] > latest_local]
            else: # assuming date is in index
                data.index = pd.to_datetime(data.index).date
                data = data[data.index > latest_local]
            
            if data.empty:
                print(f"  No truly new data after filtering for {symbol}.")
                return pd.DataFrame() # Return empty DataFrame if no new data after filtering
        
        # After all filtering, convert to tuples and bulk insert
        if data is not None and not data.empty:
            rows_to_insert = []
            for idx, row in data.iterrows():
                row_date = row['datetime'] if 'datetime' in row else idx
                if hasattr(row_date, "to_pydatetime"):
                    row_date = row_date.to_pydatetime()
                
                # Only call .date() if row_date is a datetime, not if it's already a date
                if isinstance(row_date, datetime):
                    row_date = row_date.date()
                
                rows_to_insert.append((
                    symbol,
                    row_date,
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    int(row['volume'])
                ))
            db.insert_stock_data_bulk(rows_to_insert)
            print(f"  Inserted {len(rows_to_insert)} new rows for {symbol}.")
        
        return data # Return the (potentially filtered) DataFrame
    
    def analyze_symbol(self, symbol, days=365, db=None):
        """Run all strategies on a symbol."""
        if db is None:
            db = self.db # Fallback to instance's db if not provided
        
        data = db.get_symbol_data(symbol, days)
        
        if not data:
            print(f"No data available for {symbol}")
            return []
        
        # Convert to DataFrame
        df = pd.DataFrame(
            data,
            columns=['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
        )
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        
        # Run strategies
        strategies = {
            'Swing Trading': SwingTradingStrategy(df),
            'Position Trading': PositionTradingStrategy(df),
            'Mean Reversion': AlgorithmicMeanReversionStrategy(df),
            'Price Action': PriceActionStrategy(df)
        }
        
        all_signals = []
        for strategy_name, strategy in strategies.items():
            signals = strategy.generate_signals()
            for signal in signals:
                signal_date = signal['date']
                # Handle both datetime and date objects
                if hasattr(signal_date, 'date'):
                    signal_date = signal_date.date()
                
                all_signals.append({
                    'symbol': symbol,
                    'strategy': strategy_name,
                    'signal': signal['signal'],
                    'confidence': signal['confidence'],
                    'date': signal_date
                })
        
        return all_signals
    
    def run_analysis_pipeline(self, symbols=None, days=365):
        """Run complete analysis on multiple symbols."""
        if self.db.read_only:
            raise SystemExit("Database opened in read-only mode; analysis pipeline is disabled.")
        
        if symbols is None:
            symbols = EGX_SYMBOLS  # Analyze all configured EGX symbols

        self.last_symbols = symbols
        
        print("Starting analysis pipeline...")

        index_symbol = EGX_INDEX_SYMBOL
        if index_symbol and index_symbol not in symbols:
            try:
                self.load_data(index_symbol, days)
                print(f"[index] Loaded data for {index_symbol}")
            except Exception as e:
                print(f"[index] Error loading {index_symbol}: {e}")
        
        # Use ThreadPoolExecutor for concurrent data loading
        max_workers = 5 # Limit concurrent fetches to avoid overwhelming APIs or local resources
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {executor.submit(self._process_symbol, symbol, days, self.db.db_path): symbol for symbol in symbols}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_symbol)):
                symbol = future_to_symbol[future]
                print(f"[{i+1}/{len(symbols)}] Processing {symbol}...")
                try:
                    future.result() # This will re-raise any exception caught during _process_symbol
                    print(f"  Finished processing {symbol}")
                except Exception as e:
                    print(f"  Error processing {symbol}: {e}")
        
        print("\nAnalysis complete.")
    
    def _process_symbol(self, symbol, days, db_path):
        """Helper method to load and analyze a single symbol's data."""
        # Create a new database connection for this thread
        local_db = StockDatabase(db_path=db_path)
        
        try:
            # Load data
            try:
                self.load_data(symbol, days, db=local_db)
            except Exception as e:
                print(f"  Error loading data for {symbol}: {e}")
                raise # Re-raise to be caught by the executor
            
            # Analyze
            try:
                signals = self.analyze_symbol(symbol, days, db=local_db)
                if signals:
                    local_db.insert_signals([
                        (s['symbol'], s['date'], s['strategy'], s['signal'], s['confidence'])
                        for s in signals
                    ])
                    print(f"  Found {len(signals)} signals for {symbol}")
            except Exception as e:
                print(f"  Error analyzing {symbol}: {e}")
                raise # Re-raise to be caught by the executor
        finally:
            local_db.close()
    
    def display_dashboard(self):
        """Display the dashboard summary."""
        dashboard = DashboardData(self.analysis)
        summary = dashboard.prepare_dashboard_summary(symbols=self.last_symbols)
        
        print("\n" + "="*60)
        print("          FINANCE DASHBOARD SUMMARY")
        print("="*60)
        print(f"Timestamp: {summary['timestamp']}")
        print(f"\nMarket Sentiment: {summary['market_sentiment']:.1f}%")
        index_sentiment = summary.get('index_sentiment')
        if index_sentiment is None:
            print("Index Sentiment (EGX): N/A")
        else:
            print(f"Index Sentiment (EGX): {index_sentiment:.1f}%")
        print(f"Market Memo: {summary['market_memo']}")
        
        print(f"\nGOLDEN LIST (3+ Strategy Signals):")
        if summary['golden_list']:
            for item in summary['golden_list']:
                if len(item) == 2:
                    symbol, signal_count = item
                    latest_price = None
                else:
                    symbol, signal_count, latest_price = item

                if latest_price is None:
                    print(f"  • {symbol}: {signal_count} signals")
                else:
                    print(f"  • {symbol}: {signal_count} signals (last close: {latest_price:.2f})")
        else:
            print("  (No symbols with 3+ signals)")
        
        print(f"\nTop Recommendations (Confidence >= 0.75):")
        if summary['top_signals']:
            for strategy, symbol, signal, confidence in summary['top_signals']:
                print(f"  • {strategy:20} {symbol:6} {signal:5} (conf: {confidence:.2f})")
        else:
            print("  (No high-confidence signals)")
        
        print("="*60 + "\n")

    def build_latest_table_df(self):
        """Build a latest-data table for the selected symbols."""
        symbols = self.last_symbols if self.last_symbols else EGX_SYMBOLS
        rows = []

        for symbol in symbols:
            latest = self.db.get_latest_ohlc(symbol)
            if not latest:
                continue

            date, open_price, high, low, close = latest
            signals = self.db.get_signals_for_symbol_date(symbol, date)

            if signals:
                buy_count = sum(1 for _s, sig, _c in signals if sig == "BUY")
                sell_count = sum(1 for _s, sig, _c in signals if sig == "SELL")
                if buy_count > sell_count:
                    action = "BUY"
                elif sell_count > buy_count:
                    action = "SELL"
                else:
                    action = "MIXED"

                strategies = ", ".join(sorted({s for s, _sig, _c in signals}))
                conf_vals = [float(c) for _s, _sig, c in signals if c is not None]
                avg_conf = sum(conf_vals) / len(conf_vals) if conf_vals else None
            else:
                action = "NONE"
                strategies = ""
                avg_conf = None

            if action == "BUY":
                advice = "Consider entry; confirm risk rules."
            elif action == "SELL":
                advice = "Consider exit/avoid; confirm risk rules."
            elif action == "MIXED":
                advice = "Mixed signals; wait for clarity."
            else:
                advice = "No active signals."

            rows.append({
                "Symbol": symbol,
                "Open": open_price,
                "High": high,
                "Low": low,
                "Close": close,
                "Buy/Sell": action,
                "Strategies": strategies,
                "Confidence": round(avg_conf, 2) if avg_conf is not None else None,
                "Advice": advice,
            })

        return pd.DataFrame(rows)

    def display_latest_table(self):
        """Display a latest-data table for the selected symbols."""
        df = self.build_latest_table_df()
        if df.empty:
            print("No latest data available for the selected symbols.")
            return df

        print(df.to_string(index=False))
        return df
    
    def close(self):
        """Close database connections."""
        self.db.close()

    def purge_database_file(self):
        """Delete the database file if it was a temp/mock DB."""
        if self._db_path and Path(self._db_path).exists():
            try:
                Path(self._db_path).unlink()
                print(f"Purged mock database: {self._db_path}")
            except Exception as e:
                print(f"Warning: failed to delete mock database {self._db_path}: {e}")

def _build_fetcher_factory(source):
    """Create a fetcher factory based on the requested source."""
    if source == "mock":
        return lambda _db: MockDataFetcher(seed=42) # Use a fixed seed for reproducible mock data
    if source == "tv":
        def _factory(db):
            try:
                return TVDataFeedFetcher()
            except Exception as e:
                print(f"TVDataFeedFetcher failed ({e}). Falling back to cached historical data.")
                return CachedDataFetcher(db=db)
        return _factory
    raise SystemExit(f"Unknown data source: {source}")

def _parse_args():
    parser = argparse.ArgumentParser(description="EGX trading strategy analysis")
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit."
    )
    parser.add_argument(
        "--about",
        action="store_true",
        help="Print a short description and exit."
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Open the database in read-only mode (no writes)."
    )
    parser.add_argument(
        "--backup-db",
        action="store_true",
        help="Create a timestamped backup of the database before running the pipeline."
    )
    parser.add_argument(
        "--data-source",
        choices=["mock", "tv"],
        default="tv",
        help="Data source to use: tv (TradingView via tvDatafeed) or mock (explicitly requested)."
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated list of symbols to analyze (overrides --limit)."
    )
    parser.add_argument(
        "--allow-unknown-symbols",
        action="store_true",
        help="Allow symbols not in EGX_SYMBOLS (no validation)."
    )
    parser.add_argument(
        "--sync-symbols-tv",
        action="store_true",
        help="Sync EGX symbols from TradingView (tradingview-screener) and update the cached list."
    )
    parser.add_argument(
        "--list-symbols",
        action="store_true",
        help="List all tradeable EGX symbols (from cached list or config fallback) and exit."
    )
    parser.add_argument(
        "--latest-table",
        action="store_true",
        help="Print latest data table (High, Low, Close, Buy/Sell, Strategies, Confidence, Advice) and exit."
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        default=None,
        help="Export latest table to CSV at the given path."
    )
    parser.add_argument(
        "--export-excel",
        type=str,
        default=None,
        help="Export latest table to Excel (.xlsx) at the given path."
    )
    parser.add_argument(
        "--export-pdf",
        type=str,
        default=None,
        help="Export latest table to PDF at the given path (requires reportlab)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of symbols to analyze for quick tests."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days of data to fetch/analyze."
    )
    parser.add_argument(
        "--purge-symbols",
        action="store_true",
        help="Delete existing data for each symbol before loading new data."
    )
    parser.add_argument(
        "--purge-future-rows",
        action="store_true",
        help="Delete any rows with dates after today before running."
    )
    parser.add_argument(
        "--purge-mock-after",
        action="store_true",
        help="Delete the mock database file after the run (mock data source only)."
    )
    return parser.parse_args()


def _backup_database_file(db_path):
    """Create a timestamped backup of the DuckDB file if it exists."""
    if not db_path:
        print("No database path provided for backup.")
        return None
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"No database file found to back up at {db_path}")
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_suffix(db_path.suffix + f".bak-{stamp}")
    shutil.copy2(db_path, backup_path)
    print(f"Backed up database to {backup_path}")
    return backup_path


def _has_snapshot_or_backup(db_path):
    db_path = Path(db_path)
    snapshot = db_path.with_suffix(db_path.suffix + ".snapshot")
    if snapshot.exists():
        return True
    snapshots = list(db_path.parent.glob(db_path.name + ".snapshot-*"))
    if snapshots:
        return True
    backups = list(db_path.parent.glob(db_path.name + ".bak-*"))
    return bool(backups)


def _try_acquire_writer_lock(db_path):
    lock_path = Path(db_path).with_suffix(Path(db_path).suffix + ".writer.lock")
    try:
        lock = WriterLock(lock_path, timeout=0.1, poll_interval=0.1)
        lock.acquire()
        lock.release()
        return True
    except Exception:
        return False


def _snapshot_database_file(db_path, conn=None):
    """Create a stable snapshot DB for read-only readers using ATTACH + CTAS."""
    if not db_path:
        print("No database path provided for snapshot.")
        return None
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"No database file found to snapshot at {db_path}")
        return None
    if conn is None:
        print("No live database connection available for snapshot.")
        return None

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    snapshot_path = db_path.with_suffix(db_path.suffix + f".snapshot-{stamp}")

    try:
        snap_path_sql = str(snapshot_path).replace("'", "''")
        conn.execute(f"ATTACH '{snap_path_sql}' AS snap")
        tables = conn.execute("PRAGMA show_tables").fetchall()
        for (table_name,) in tables:
            conn.execute(f"DROP TABLE IF EXISTS snap.{table_name}")
            conn.execute(f"CREATE TABLE snap.{table_name} AS SELECT * FROM main.{table_name}")
        conn.execute("DETACH snap")
        print(f"Snapshot written to {snapshot_path}")

        # Atomically update the stable snapshot name.
        stable_snapshot = db_path.with_suffix(db_path.suffix + ".snapshot")
        try:
            os.replace(snapshot_path, stable_snapshot)
        except Exception:
            # If replace fails, leave timestamped snapshot as a fallback.
            pass

        return snapshot_path
    except Exception as e:
        print(f"Snapshot failed: {e}")
        try:
            conn.execute("DETACH snap")
        except Exception:
            pass
        return None


def _run_write_flow(app, args, symbols):
    if args.backup_db:
        _backup_database_file(app.db.db_path)

    if args.purge_future_rows:
        cutoff = datetime.now().date()
        app.db.delete_future_rows(cutoff)
        print(f"Purged rows after {cutoff}")

    # Run the pipeline
    app.run_analysis_pipeline(symbols=symbols, days=args.days)
    _snapshot_database_file(app.db.db_path, conn=app.db.conn)

    if args.latest_table or args.export_csv or args.export_excel or args.export_pdf:
        df = app.display_latest_table()

        if args.export_csv:
            df.to_csv(args.export_csv, index=False)
            print(f"Exported CSV to {args.export_csv}")

        if args.export_excel:
            df.to_excel(args.export_excel, index=False)
            print(f"Exported Excel to {args.export_excel}")

        if args.export_pdf:
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import letter, landscape
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

                pdf = SimpleDocTemplate(args.export_pdf, pagesize=landscape(letter))
                data = [df.columns.tolist()] + df.astype(str).values.tolist()
                table = Table(data)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]))
                pdf.build([table])
                print(f"Exported PDF to {args.export_pdf}")
            except Exception as e:
                print(f"PDF export failed: {e}")
    else:
        app.display_dashboard()


if __name__ == "__main__":
    is_streamlit = any("streamlit" in arg.lower() for arg in sys.argv) or "streamlit" in sys.modules

    if is_streamlit:
        # Allow "streamlit run app.py" to render the UI.
        import dashboard  # noqa: F401
    else:
        args, _unknown = _parse_args(), None
        if args.version:
            print(__version__)
            sys.exit(0)

        if args.about:
            print(__about__)
            sys.exit(0)

        fetcher_factory = _build_fetcher_factory(args.data_source)

        if args.list_symbols:
            for s in EGX_SYMBOLS:
                print(s)
            sys.exit(0)

        if args.sync_symbols_tv:
            try:
                result = sync_symbols_from_tradingview(EGX_SYMBOLS)
                print(f"Synced {len(result.active_symbols)} active symbols to {result.csv_path}")
                print(f"Dormant symbols removed: {len(result.dormant_symbols)}")
                print(f"Missing in config: {len(result.missing_in_config)}")
                print(f"Missing in TradingView: {len(result.missing_in_tv)}")
                print(f"Report saved to: {result.report_path}")
            except Exception as e:
                print(f"Failed to sync symbols from TradingView: {e}")
                sys.exit(1)
            sys.exit(0)

        if args.symbols:
            requested = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
            if args.allow_unknown_symbols:
                symbols = requested
            else:
                known = set(EGX_SYMBOLS)
                allowed = set(EGX_SYMBOLS)
                if EGX_INDEX_SYMBOL:
                    allowed.add(EGX_INDEX_SYMBOL)

                unknown = [s for s in requested if s not in allowed]
                for s in unknown:
                    print(f"Unknown symbol (not in EGX_SYMBOLS): {s}")

                symbols = [s for s in requested if s in allowed]
                if not symbols:
                    print("No valid symbols to analyze. Exiting.")
                    sys.exit(1)
        elif args.limit:
            symbols = EGX_SYMBOLS[:args.limit]
        else:
            symbols = None

        mock_db_path = None
        purge_mock_after = args.purge_mock_after
        if args.data_source == "mock":
            mock_db_path = DATA_DIR / "stocks_mock.duckdb"
            if not args.purge_mock_after:
                purge_mock_after = True

        db_path_for_check = mock_db_path if mock_db_path else DB_PATH

        if args.read_only and not _has_snapshot_or_backup(db_path_for_check):
            if _try_acquire_writer_lock(db_path_for_check):
                print("No snapshot found; running pipeline once to generate a snapshot.")
                app = FinanceApp(
                    fetcher_factory=fetcher_factory,
                    purge_on_load=args.purge_symbols,
                    db_path=mock_db_path,
                    read_only=False
                )
                try:
                    _run_write_flow(app, args, symbols)
                finally:
                    app.close()
                sys.exit(0)

        try:
            app = FinanceApp(
                fetcher_factory=fetcher_factory,
                purge_on_load=args.purge_symbols,
                db_path=mock_db_path,
                read_only=args.read_only
            )
        except Exception as e:
            if not args.read_only:
                print("Writer is busy. Falling back to read-only mode.")
                args.read_only = True
                app = FinanceApp(
                    fetcher_factory=fetcher_factory,
                    purge_on_load=args.purge_symbols,
                    db_path=mock_db_path,
                    read_only=True
                )
            else:
                raise
        
        try:
            if args.read_only:
                if args.latest_table or args.export_csv or args.export_excel or args.export_pdf:
                    df = app.display_latest_table()
                    if args.export_csv:
                        df.to_csv(args.export_csv, index=False)
                        print(f"Exported CSV to {args.export_csv}")
                    if args.export_excel:
                        df.to_excel(args.export_excel, index=False)
                        print(f"Exported Excel to {args.export_excel}")
                    if args.export_pdf:
                        try:
                            from reportlab.lib import colors
                            from reportlab.lib.pagesizes import letter, landscape
                            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

                            pdf = SimpleDocTemplate(args.export_pdf, pagesize=landscape(letter))
                            data = [df.columns.tolist()] + df.astype(str).values.tolist()
                            table = Table(data)
                            table.setStyle(TableStyle([
                                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ]))
                            pdf.build([table])
                            print(f"Exported PDF to {args.export_pdf}")
                        except Exception as e:
                            print(f"PDF export failed: {e}")
                else:
                    app.display_dashboard()
                sys.exit(0)

            _run_write_flow(app, args, symbols)
        
        finally:
            app.close()
            if purge_mock_after and args.data_source == "mock":
                app.purge_database_file()
