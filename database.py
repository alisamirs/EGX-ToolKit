"""Database operations for DuckDB."""

import duckdb
from pathlib import Path
from config import DB_PATH
import threading
import time
import os
import shutil


class WriterLock:
    """Process-wide exclusive writer lock using a lock file."""

    def __init__(self, lock_path, timeout=10.0, poll_interval=0.1):
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._fh = None

    def acquire(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.lock_path, "a+")
        start = time.time()

        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except Exception:
                if time.time() - start >= self.timeout:
                    raise RuntimeError(
                        f"Writer lock busy: {self.lock_path}. "
                        "Another process is writing. Use --read-only or try again later."
                    )
                time.sleep(self.poll_interval)

    def release(self):
        if not self._fh:
            return
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None


class StockDatabase:
    """Manages DuckDB operations for stock data with thread-safety."""

    _process_writer_lock = None
    _process_writer_lock_count = 0
    
    def __init__(self, db_path=DB_PATH, read_only=False):
        self.db_path = db_path
        self.conn = None
        self.read_only = read_only
        self._lock = threading.RLock()  # Recursive lock for thread-safe access
        self._writer_lock = None
        self._connect()
        self._acquire_writer_lock_if_needed()
    
    def _connect(self):
        """Establish connection to DuckDB."""
        # Each thread gets its own connection for better concurrency
        # DuckDB supports multiple readers and one writer
        conn_config = {}
        if self.read_only:
            # Read-only always uses historical snapshots/backups.
            if not Path(self.db_path).exists():
                raise RuntimeError("Database file not found for read-only mode.")

            wait_seconds = float(os.getenv("EGX_READONLY_WAIT_SECONDS", "120"))
            deadline = time.time() + wait_seconds
            while True:
                snapshot_path = Path(self.db_path).with_suffix(Path(self.db_path).suffix + ".snapshot")
                snapshots = sorted(Path(self.db_path).parent.glob(Path(self.db_path).name + ".snapshot-*"), reverse=True)
                backups = sorted(Path(self.db_path).parent.glob(Path(self.db_path).name + ".bak-*"), reverse=True)

                candidates = []
                if snapshot_path.exists():
                    candidates.append(snapshot_path)
                candidates.extend(snapshots)
                candidates.extend(backups)

                if candidates:
                    self.conn = duckdb.connect(str(candidates[0]), read_only=True)
                    return

                if time.time() >= deadline:
                    raise RuntimeError(
                        "Read-only requires a snapshot or backup. "
                        "Run `python app.py` once to generate a snapshot, "
                        "or wait for the writer to finish."
                    )
                time.sleep(1.0)
        else:
            self.conn = duckdb.connect(str(self.db_path), **conn_config)

    def _acquire_writer_lock_if_needed(self):
        """Acquire a process-wide writer lock for exclusive write access."""
        if self.read_only:
            return
        if StockDatabase._process_writer_lock is None:
            timeout = float(os.getenv("EGX_WRITER_TIMEOUT", "10"))
            lock_path = Path(self.db_path).with_suffix(Path(self.db_path).suffix + ".writer.lock")
            lock = WriterLock(lock_path, timeout=timeout)
            lock.acquire()
            StockDatabase._process_writer_lock = lock
            StockDatabase._process_writer_lock_count = 1
        else:
            StockDatabase._process_writer_lock_count += 1
    
    def create_tables(self):
        """Create necessary tables if they don't exist."""
        with self._lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS stocks (
                    symbol VARCHAR,
                    date DATE,
                    open DECIMAL(10, 4),
                    high DECIMAL(10, 4),
                    low DECIMAL(10, 4),
                    close DECIMAL(10, 4),
                    volume BIGINT,
                    PRIMARY KEY (symbol, date)
                )
            """)
            
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS indicators (
                    symbol VARCHAR,
                    date DATE,
                    ema_20 DECIMAL(10, 4),
                    ema_50 DECIMAL(10, 4),
                    sma_200 DECIMAL(10, 4),
                    rsi DECIMAL(5, 2),
                    bb_upper DECIMAL(10, 4),
                    bb_middle DECIMAL(10, 4),
                    bb_lower DECIMAL(10, 4),
                    vwap DECIMAL(10, 4),
                    PRIMARY KEY (symbol, date)
                )
            """)
            
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    symbol VARCHAR,
                    date DATE,
                    strategy VARCHAR,
                    signal VARCHAR,
                    confidence DECIMAL(3, 2),
                    PRIMARY KEY (symbol, date, strategy)
                )
            """)
    
    def insert_stock_data(self, symbol, date, open_price, high, low, close, volume):
        """Insert or update stock price data."""
        with self._lock:
            self.conn.execute("""
                INSERT OR REPLACE INTO stocks (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [symbol, date, open_price, high, low, close, volume])
    
    def insert_stock_data_bulk(self, data_rows):
        """Insert or update multiple stock price data rows."""
        if not data_rows:
            return
        with self._lock:
            self.conn.executemany("""
                INSERT OR REPLACE INTO stocks (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data_rows)

    def delete_symbol_data(self, symbol, date_after=None):
        """Delete stock data for a symbol, optionally only after a date."""
        with self._lock:
            if date_after:
                self.conn.execute(
                    "DELETE FROM stocks WHERE symbol = ? AND date > ?",
                    [symbol, date_after]
                )
            else:
                self.conn.execute(
                    "DELETE FROM stocks WHERE symbol = ?",
                    [symbol]
                )

    def delete_future_rows(self, cutoff_date):
        """Delete any stock rows with date greater than cutoff_date."""
        with self._lock:
            self.conn.execute(
                "DELETE FROM stocks WHERE date > ?",
                [cutoff_date]
            )
    
    def get_latest_date_for_symbol(self, symbol):
        """Get the latest date available for a symbol."""
        with self._lock:
            result = self.conn.execute(
                "SELECT MAX(date) FROM stocks WHERE symbol = ?", [symbol]
            ).fetchall()
            return result[0][0] if result and result[0][0] else None
    
    def get_symbol_data(self, symbol, days=None):
        """Get stock data for a symbol."""
        with self._lock:
            if days:
                query = """
                    SELECT * FROM (
                        SELECT * FROM stocks
                        WHERE symbol = ?
                        ORDER BY date DESC
                        LIMIT ?
                    )
                    ORDER BY date ASC
                """
                return self.conn.execute(query, [symbol, days]).fetchall()
            else:
                query = "SELECT * FROM stocks WHERE symbol = ? ORDER BY date"
                return self.conn.execute(query, [symbol]).fetchall()

    def get_full_symbol_data(self, symbol, days=None):
        """
        Get combined stock data (OHLCV) and technical indicators for a symbol.
        Returns a list of tuples, or an empty list if no data.
        """
        with self._lock:
            query = """
                SELECT
                    s.date,
                    s.open::DOUBLE,
                    s.high::DOUBLE,
                    s.low::DOUBLE,
                    s.close::DOUBLE,
                    s.volume,
                    i.ema_20::DOUBLE,
                    i.ema_50::DOUBLE,
                    i.sma_200::DOUBLE,
                    i.rsi::DOUBLE,
                    i.bb_upper::DOUBLE,
                    i.bb_middle::DOUBLE,
                    i.bb_lower::DOUBLE,
                    i.vwap::DOUBLE
                FROM stocks s
                LEFT JOIN indicators i ON s.symbol = i.symbol AND s.date = i.date
                WHERE s.symbol = ?
            """
            params = [symbol]

            if days:
                # Subquery to limit by days, then order by date ascending
                query += """
                    ORDER BY s.date DESC
                    LIMIT ?
                """
                params.append(days)

            query = f"SELECT * FROM ({query}) ORDER BY date ASC" # Ensure final output is ordered ascending

            return self.conn.execute(query, params).fetchall()

    def get_symbol_close_series(self, symbol, days=None, end_date=None):
        """Get date/close series for a symbol, optionally limited by days and end_date."""
        with self._lock:
            base_query = """
                SELECT date, close
                FROM stocks
                WHERE symbol = ?
            """
            params = [symbol]

            if end_date:
                base_query += " AND date <= ?"
                params.append(end_date)

            if days:
                # If days is specified, we need a subquery to limit the rows before the final order
                query = f"""
                    SELECT * FROM ({base_query} ORDER BY date DESC LIMIT ?)
                    ORDER BY date ASC
                """
                params.append(days)
            else:
                # Otherwise, just order the base query
                query = f"{base_query} ORDER BY date ASC"

            return self.conn.execute(query, params).fetchall()

    def get_latest_close_price(self, symbol):
        """Get the latest closing price for a given symbol."""
        with self._lock:
            query = """
                SELECT close::DOUBLE
                FROM stocks
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT 1
            """
            result = self.conn.execute(query, [symbol]).fetchone()
            return result[0] if result else None

    def get_latest_ohlc(self, symbol):
        """Get latest date and OHLC for a given symbol."""
        with self._lock:
            query = """
                SELECT date, open::DOUBLE, high::DOUBLE, low::DOUBLE, close::DOUBLE
                FROM stocks
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT 1
            """
            result = self.conn.execute(query, [symbol]).fetchone()
            return result if result else None

    def get_signals_for_symbol_date(self, symbol, date):
        """Get signals for a specific symbol and date."""
        with self._lock:
            query = """
                SELECT strategy, signal, confidence
                FROM signals
                WHERE symbol = ? AND date = ?
            """
            return self.conn.execute(query, [symbol, date]).fetchall()

    def get_signals_for_symbol(self, symbol):
        """Get all signals for a specific symbol."""
        with self._lock:
            query = "SELECT date, strategy, signal, confidence FROM signals WHERE symbol = ? ORDER BY date"
            return self.conn.execute(query, [symbol]).fetchall()

    def insert_signal(self, symbol, date, strategy, signal, confidence):
        """Insert or update a strategy signal."""
        with self._lock:
            self.conn.execute("""
                INSERT OR REPLACE INTO signals (symbol, date, strategy, signal, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, [symbol, date, strategy, signal, confidence])

    def insert_signals(self, signals):
        """Insert or update multiple signals."""
        if not signals:
            return
        with self._lock:
            self.conn.executemany("""
                INSERT OR REPLACE INTO signals (symbol, date, strategy, signal, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, signals)

    def get_latest_signal_date(self):
        """Get the latest signal date available."""
        with self._lock:
            result = self.conn.execute(
                "SELECT MAX(date) FROM signals"
            ).fetchall()
            return result[0][0] if result and result[0][0] else None

    def get_latest_stock_date(self):
        """Get the latest stock date available."""
        with self._lock:
            result = self.conn.execute(
                "SELECT MAX(date) FROM stocks"
            ).fetchall()
            return result[0][0] if result and result[0][0] else None
    
    def close(self):
        """Close database connection."""
        with self._lock:
            if self.conn:
                self.conn.close()
        if getattr(self, "_readonly_shadow_path", None):
            try:
                Path(self._readonly_shadow_path).unlink()
            except Exception:
                pass
        if not self.read_only and StockDatabase._process_writer_lock is not None:
            StockDatabase._process_writer_lock_count -= 1
            if StockDatabase._process_writer_lock_count <= 0:
                StockDatabase._process_writer_lock.release()
                StockDatabase._process_writer_lock = None
                StockDatabase._process_writer_lock_count = 0
