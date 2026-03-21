"""Fetch stock data from external sources."""

from datetime import datetime, timedelta
from config import EGX_SYMBOLS
import pandas as pd


class DataFetcher:
    """Abstract data fetcher for stock prices."""
    
    def __init__(self):
        pass
    
    def fetch_symbol_data(self, symbol, days=365):
        """Fetch data for a single symbol."""
        raise NotImplementedError
    
    def fetch_all_symbols(self, days=365):
        """Fetch data for all symbols."""
        data = {}
        for symbol in EGX_SYMBOLS:
            try:
                data[symbol] = self.fetch_symbol_data(symbol, days)
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
        return data


class TVDataFeedFetcher(DataFetcher):
    """Fetcher using tvDatafeed library."""
    
    def __init__(self):
        super().__init__()
        try:
            from tvDatafeed import TvDatafeed, Interval
            self.tv = TvDatafeed()
            self.interval = Interval.in_daily
            self._cache = {}  # In-memory cache: {(symbol, days): dataframe}
        except ImportError:
            raise ImportError("tvDatafeed not installed. Install with: pip install tvDatafeed")
    
    def fetch_symbol_data(self, symbol, days=365):
        """Fetch data from TradingView using tvDatafeed."""
        cache_key = (symbol, days)
        if cache_key in self._cache:
            print(f"  [Cache] Returning data for {symbol} from cache.")
            return self._cache[cache_key].copy() # Return a copy to prevent external modification
        
        try:
            # tvDatafeed format: symbol, exchange
            data = self.tv.get_hist(
                symbol=symbol,
                exchange='EGX',
                interval=self.interval,  # 1 day
                n_bars=days
            )
            if data is not None and not data.empty:
                self._cache[cache_key] = data.copy()
            return data
        except Exception as e:
            print(f"Error fetching {symbol} from TradingView: {e}")
            return None


class CachedDataFetcher(DataFetcher):
    """Fetcher that reads historical/cached data from the database."""
    
    def __init__(self, db=None):
        super().__init__()
        self.db = db
    
    def fetch_symbol_data(self, symbol, days=365):
        """Fetch historical data from the database cache."""
        if not self.db:
            return None
        
        try:
            data_tuples = self.db.get_symbol_data(symbol, days=days)
            if not data_tuples:
                print(f"No cached data available for {symbol}")
                return None
            
            # Convert database tuples to DataFrame
            data = []
            for row in data_tuples:
                data.append({
                    'datetime': row[1],  # date column
                    'open': row[2],      # open
                    'high': row[3],      # high
                    'low': row[4],       # low
                    'close': row[5],     # close
                    'volume': row[6]     # volume
                })
            
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Error fetching cached data for {symbol}: {e}")
            return None


class MockDataFetcher(DataFetcher):
    """Mock fetcher for testing without real API."""
    
    def __init__(self, seed=None):
        super().__init__()
        if seed is not None:
            import random
            random.seed(seed)
    
    def fetch_symbol_data(self, symbol, days=365):
        """Generate mock data for testing."""
        import random
        dates = pd.date_range(end=datetime.now(), periods=days)
        base_price = random.uniform(50, 500)
        
        data = []
        for date in dates:
            close = base_price + random.uniform(-5, 5)
            data.append({
                'datetime': date,
                'open': close + random.uniform(-2, 2),
                'high': close + random.uniform(0, 5),
                'low': close - random.uniform(0, 5),
                'close': close,
                'volume': random.randint(100000, 10000000)
            })
            base_price = close
        
        return pd.DataFrame(data)
