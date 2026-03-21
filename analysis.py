"""Analysis engine for aggregating signals and market sentiment."""

from datetime import datetime
from database import StockDatabase
from config import MIN_SIGNAL_COUNT, EGX_INDEX_SYMBOL
import pandas as pd


class AnalysisEngine:
    """Aggregates signals and generates market analysis."""
    
    def __init__(self, db):
        self.db = db

    def _resolve_date(self, date):
        """Resolve analysis date to latest signal date if none provided."""
        if date is not None:
            return date
        latest_signal = self.db.get_latest_signal_date()
        if latest_signal:
            return latest_signal
        latest_stock = self.db.get_latest_stock_date()
        if latest_stock:
            return latest_stock
        return datetime.now().date()
    
    def get_signal_count_by_symbol(self, date=None, symbols=None):
        """Get number of strategies that triggered for each symbol."""
        date = self._resolve_date(date)
        
        params = [date]
        symbol_filter = ""
        if symbols:
            symbol_filter = " AND symbol IN ({})".format(",".join(["?"] * len(symbols)))
            params.extend(symbols)

        query = f"""
            SELECT symbol, COUNT(DISTINCT strategy) as signal_count
            FROM signals
            WHERE date = ?{symbol_filter}
            GROUP BY symbol
            ORDER BY signal_count DESC
        """
        result = self.db.conn.execute(query, params).fetchall()
        return result
    
    def get_golden_list(self, min_signals=MIN_SIGNAL_COUNT, date=None, symbols=None):
        """Get stocks with signals from 3+ strategies, including their latest close price."""
        signals_count = self.get_signal_count_by_symbol(date, symbols=symbols)
        golden_list = []
        for symbol, count in signals_count:
            if count >= min_signals:
                latest_price = self.db.get_latest_close_price(symbol)
                if latest_price is not None:
                    golden_list.append((symbol, count, latest_price))
        return golden_list
    
    def get_market_sentiment(self, date=None, symbols=None):
        """Calculate market sentiment based on signal ratios."""
        date = self._resolve_date(date)

        params = [date]
        symbol_filter = ""
        if symbols:
            symbol_filter = " AND symbol IN ({})".format(",".join(["?"] * len(symbols)))
            params.extend(symbols)

        query = f"""
            SELECT signal, COUNT(*) as count
            FROM signals
            WHERE date = ?{symbol_filter}
            GROUP BY signal
        """
        result = self.db.conn.execute(query, params).fetchall()
        
        buy_count = sum(count for sig, count in result if sig == 'BUY')
        sell_count = sum(count for sig, count in result if sig == 'SELL')
        
        if buy_count + sell_count == 0:
            return 50  # Neutral
        
        sentiment = (buy_count / (buy_count + sell_count)) * 100
        return sentiment

    def get_index_sentiment(self, date=None, symbol=EGX_INDEX_SYMBOL):
        """
        Calculate market sentiment based on EGX index price action.
        Returns a score from 0-100, or None if insufficient data.
        """
        if not symbol:
            return None

        if date is None:
            date = self.db.get_latest_date_for_symbol(symbol)
        if date is None:
            return None

        series = self.db.get_symbol_close_series(symbol, days=260, end_date=date)
        if len(series) < 200:
            return None

        df = pd.DataFrame(series, columns=['date', 'close'])
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df.dropna(inplace=True)

        if len(df) < 200:
            return None

        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        df['ret_20'] = df['close'].pct_change(20)

        last = df.iloc[-1]
        if pd.isna(last['sma_50']) or pd.isna(last['sma_200']) or pd.isna(last['ret_20']):
            return None

        score = 50
        score += 20 if last['close'] > last['sma_50'] else -20
        score += 20 if last['sma_50'] > last['sma_200'] else -20
        score += 10 if last['ret_20'] > 0 else -10
        score += 10 if last['close'] > last['sma_200'] else -10

        return max(0, min(100, score))
    
    def get_strategy_recommendations(self, date=None, symbols=None):
        """Get high-conviction signals by strategy."""
        date = self._resolve_date(date)

        params = [date]
        symbol_filter = ""
        if symbols:
            symbol_filter = " AND symbol IN ({})".format(",".join(["?"] * len(symbols)))
            params.extend(symbols)

        query = f"""
            SELECT strategy, symbol, signal, confidence
            FROM signals
            WHERE date = ? AND confidence >= 0.75{symbol_filter}
            ORDER BY strategy, confidence DESC
            LIMIT 10
        """
        return self.db.conn.execute(query, params).fetchall()
    
    def generate_market_memo(self, sentiment):
        """Generate a brief market summary."""
        if sentiment > 65:
            return "Market is bullish; favor Swing Trading and Position Trading strategies."
        elif sentiment > 50:
            return "Market is slightly bullish; mixed signals. Price Action and Algorithmic strategies may be better."
        elif sentiment > 35:
            return "Market is slightly bearish; caution advised. Focus on short-term strategies like Scalping."
        else:
            return "Market is bearish; recommend defensive positions. Consider Mean Reversion strategies."


class DashboardData:
    """Prepares data for dashboard display."""
    
    def __init__(self, analysis_engine):
        self.engine = analysis_engine
    
    def prepare_dashboard_summary(self, date=None, symbols=None):
        """Prepare all dashboard data."""
        sentiment = self.engine.get_market_sentiment(date, symbols=symbols)
        index_sentiment = self.engine.get_index_sentiment(date)
        golden_list = self.engine.get_golden_list(date=date, symbols=symbols)
        recommendations = self.engine.get_strategy_recommendations(date, symbols=symbols)
        memo = self.engine.generate_market_memo(sentiment)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'market_sentiment': sentiment,
            'index_sentiment': index_sentiment,
            'market_memo': memo,
            'golden_list': golden_list,
            'top_signals': recommendations
        }
