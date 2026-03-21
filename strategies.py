"""Trading strategy implementations."""

import pandas as pd
from config import (
    EMA_SHORT, EMA_LONG, SMA_LONG, RSI_PERIOD,
    BB_PERIOD, BB_STD_DEV, RSI_OVERBOUGHT, RSI_OVERSOLD
)


class StrategyEngine:
    """Base class for trading strategies."""
    
    def __init__(self, data):
        """Initialize with price data."""
        self.data = data.copy()
        self.signals = []
    
    def calculate_ema(self, period):
        """Calculate Exponential Moving Average."""
        return self.data['close'].ewm(span=period).mean()
    
    def calculate_sma(self, period):
        """Calculate Simple Moving Average."""
        return self.data['close'].rolling(window=period).mean()
    
    def calculate_rsi(self, period=RSI_PERIOD):
        """Calculate Relative Strength Index."""
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_bollinger_bands(self, period=BB_PERIOD, std_dev=BB_STD_DEV):
        """Calculate Bollinger Bands."""
        sma = self.calculate_sma(period)
        std = self.data['close'].rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower
    
    def generate_signals(self):
        """Generate trading signals."""
        raise NotImplementedError


class SwingTradingStrategy(StrategyEngine):
    """20/50 EMA Cross + RSI strategy."""
    
    def generate_signals(self):
        """Detect EMA crosses and RSI conditions."""
        ema_20 = self.calculate_ema(EMA_SHORT)
        ema_50 = self.calculate_ema(EMA_LONG)
        rsi = self.calculate_rsi()
        
        self.data['ema_20'] = ema_20
        self.data['ema_50'] = ema_50
        self.data['rsi'] = rsi
        
        signals = []
        for i in range(1, len(self.data)):
            if self.data['ema_20'].iloc[i] > self.data['ema_50'].iloc[i] and \
               self.data['ema_20'].iloc[i-1] <= self.data['ema_50'].iloc[i-1]:
                signals.append({'date': self.data.index[i], 'signal': 'BUY', 'confidence': 0.8})
            elif self.data['ema_20'].iloc[i] < self.data['ema_50'].iloc[i] and \
                 self.data['ema_20'].iloc[i-1] >= self.data['ema_50'].iloc[i-1]:
                signals.append({'date': self.data.index[i], 'signal': 'SELL', 'confidence': 0.8})
            elif self.data['rsi'].iloc[i] > RSI_OVERBOUGHT:
                signals.append({'date': self.data.index[i], 'signal': 'SELL', 'confidence': 0.6})
            elif self.data['rsi'].iloc[i] < RSI_OVERSOLD:
                signals.append({'date': self.data.index[i], 'signal': 'BUY', 'confidence': 0.6})
        
        return signals


class PositionTradingStrategy(StrategyEngine):
    """200-day SMA strategy."""
    
    def generate_signals(self):
        """Detect price position relative to 200 SMA."""
        sma_200 = self.calculate_sma(SMA_LONG)
        self.data['sma_200'] = sma_200
        
        signals = []
        for i in range(SMA_LONG, len(self.data)):
            if self.data['close'].iloc[i] > sma_200.iloc[i] and \
               self.data['close'].iloc[i-1] <= sma_200.iloc[i-1]:
                signals.append({'date': self.data.index[i], 'signal': 'BUY', 'confidence': 0.75})
            elif self.data['close'].iloc[i] < sma_200.iloc[i] and \
                 self.data['close'].iloc[i-1] >= sma_200.iloc[i-1]:
                signals.append({'date': self.data.index[i], 'signal': 'SELL', 'confidence': 0.75})
        
        return signals


class AlgorithmicMeanReversionStrategy(StrategyEngine):
    """Bollinger Bands mean reversion strategy."""
    
    def generate_signals(self):
        """Generate signals based on BB and mean reversion."""
        upper, middle, lower = self.calculate_bollinger_bands()
        self.data['bb_upper'] = upper
        self.data['bb_middle'] = middle
        self.data['bb_lower'] = lower
        
        signals = []
        for i in range(BB_PERIOD, len(self.data)):
            if self.data['close'].iloc[i] <= lower.iloc[i]:
                signals.append({'date': self.data.index[i], 'signal': 'BUY', 'confidence': 0.85})
            elif self.data['close'].iloc[i] >= upper.iloc[i]:
                signals.append({'date': self.data.index[i], 'signal': 'SELL', 'confidence': 0.85})
            elif self.data['close'].iloc[i] >= middle.iloc[i] and \
                 self.data['close'].iloc[i-1] < middle.iloc[i-1]:
                signals.append({'date': self.data.index[i], 'signal': 'SELL', 'confidence': 0.6})
        
        return signals


class PriceActionStrategy(StrategyEngine):
    """Pattern detection: Engulfing, Hammer."""
    
    def is_engulfing(self, i):
        """Detect engulfing candle pattern."""
        if i < 1:
            return False
        prev = self.data.iloc[i-1]
        curr = self.data.iloc[i]
        return (curr['open'] < prev['close'] and curr['close'] > prev['open']) or \
               (curr['open'] > prev['close'] and curr['close'] < prev['open'])
    
    def is_hammer(self, i):
        """Detect hammer pattern."""
        if i < 1:
            return False
        candle = self.data.iloc[i]
        body = abs(candle['close'] - candle['open'])
        wick = min(candle['open'], candle['close']) - candle['low']
        return wick > 2 * body
    
    def generate_signals(self):
        """Generate price action signals."""
        signals = []
        for i in range(1, len(self.data)):
            if self.is_engulfing(i):
                signal = 'BUY' if self.data.iloc[i]['close'] > self.data.iloc[i]['open'] else 'SELL'
                signals.append({'date': self.data.index[i], 'signal': signal, 'confidence': 0.7})
            elif self.is_hammer(i):
                signals.append({'date': self.data.index[i], 'signal': 'BUY', 'confidence': 0.65})
        
        return signals
