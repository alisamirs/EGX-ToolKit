"""Streamlit dashboard for the Finance application."""

import streamlit as st
from datetime import datetime, timedelta
from database import StockDatabase
from analysis import AnalysisEngine, DashboardData
import pandas as pd
import plotly.graph_objects as go
from config import EGX_SYMBOLS, EGX_INDEX_SYMBOL



st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("📊 EGX Trading Strategy Dashboard")

selected_symbol = st.selectbox("Select an EGX Stock Symbol", EGX_SYMBOLS)


# Initialize database (read-only to allow parallel usage)
db = StockDatabase(read_only=True)
analysis = AnalysisEngine(db)
dashboard = DashboardData(analysis)

# Display dashboard data
col1, col2, col3, col4 = st.columns(4)

with col1:
    sentiment = analysis.get_market_sentiment()
    sentiment_color = "🟢" if sentiment > 60 else "🟡" if sentiment > 40 else "🔴"
    st.metric("Signals Sentiment", f"{sentiment:.1f}%", delta=f"{sentiment_color}")

with col2:
    index_sentiment = analysis.get_index_sentiment()
    if index_sentiment is None:
        st.metric(f"Index Sentiment ({EGX_INDEX_SYMBOL})", "N/A")
    else:
        index_color = "🟢" if index_sentiment > 60 else "🟡" if index_sentiment > 40 else "🔴"
        st.metric(f"Index Sentiment ({EGX_INDEX_SYMBOL})", f"{index_sentiment:.1f}%", delta=f"{index_color}")

with col3:
    golden_list = analysis.get_golden_list()
    st.metric("Golden List Stocks", len(golden_list))

with col4:
    recommendations = analysis.get_strategy_recommendations()
    st.metric("High Confidence Signals", len(recommendations))

# Market Memo
st.subheader("Market Memo")
memo = analysis.generate_market_memo(sentiment)
st.info(memo)

# Golden List
st.subheader("🌟 Golden List (3+ Strategy Signals)")
golden_list = analysis.get_golden_list()
if golden_list:
    golden_df = pd.DataFrame(golden_list, columns=['Symbol', 'Signal Count', 'Latest Price'])
    st.dataframe(golden_df, use_container_width=True)
else:
    st.write("No symbols with 3+ signals detected.")

# Top Signals
st.subheader("📊 Top Recommendations")
recommendations = analysis.get_strategy_recommendations()
if recommendations:
    rec_df = pd.DataFrame(recommendations, columns=['Strategy', 'Symbol', 'Signal', 'Confidence'])
    st.dataframe(rec_df, use_container_width=True)
else:
    st.write("No high-confidence signals available.")

# --- Detailed Symbol Analysis ---
st.subheader(f"📈 Detailed Analysis for {selected_symbol}")

if selected_symbol:
    full_data = db.get_full_symbol_data(selected_symbol)

    if full_data:
        # Define columns for the DataFrame based on the SQL query in get_full_symbol_data
        columns = [
            'date', 'open', 'high', 'low', 'close', 'volume',
            'ema_20', 'ema_50', 'sma_200', 'rsi',
            'bb_upper', 'bb_middle', 'bb_lower', 'vwap'
        ]
        df = pd.DataFrame(full_data, columns=columns)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)

        # Fetch signals for the selected symbol
        symbol_signals = db.get_signals_for_symbol(selected_symbol)
        signals_df = pd.DataFrame(symbol_signals, columns=['date', 'strategy', 'signal', 'confidence'])
        signals_df['date'] = pd.to_datetime(signals_df['date'])

        # Create the candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Candlesticks'
        )])

        # Add EMA_20, EMA_50, SMA_200
        fig.add_trace(go.Scatter(x=df.index, y=df['ema_20'], mode='lines', name='EMA 20', line=dict(color='blue', width=1)))
        fig.add_trace(go.Scatter(x=df.index, y=df['ema_50'], mode='lines', name='EMA 50', line=dict(color='orange', width=1)))
        fig.add_trace(go.Scatter(x=df.index, y=df['sma_200'], mode='lines', name='SMA 200', line=dict(color='purple', width=1)))

        # Add Bollinger Bands
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_upper'], mode='lines', name='BB Upper', line=dict(color='green', width=1, dash='dash')))
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_middle'], mode='lines', name='BB Middle', line=dict(color='gray', width=1, dash='dot')))
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_lower'], mode='lines', name='BB Lower', line=dict(color='green', width=1, dash='dash')))

        # Add Buy/Sell Signals
        if not signals_df.empty:
            buy_signals = signals_df[signals_df['signal'] == 'BUY']
            sell_signals = signals_df[signals_df['signal'] == 'SELL']

            if not buy_signals.empty:
                # Merge with df to get the 'low' price for placing buy markers
                buy_plot_data = pd.merge(buy_signals, df[['low']], left_on='date', right_index=True)
                fig.add_trace(go.Scatter(
                    x=buy_plot_data['date'],
                    y=buy_plot_data['low'] * 0.98, # Place marker slightly below low
                    mode='markers',
                    marker=dict(symbol='triangle-up', size=10, color='green'),
                    name='BUY Signal',
                    hovertext=[f"Strategy: {s} | Conf: {c:.2f}" for s, c in zip(buy_plot_data['strategy'], buy_plot_data['confidence'])],
                    hoverinfo='text'
                ))
            if not sell_signals.empty:
                # Merge with df to get the 'high' price for placing sell markers
                sell_plot_data = pd.merge(sell_signals, df[['high']], left_on='date', right_index=True)
                fig.add_trace(go.Scatter(
                    x=sell_plot_data['date'],
                    y=sell_plot_data['high'] * 1.02, # Place marker slightly above high
                    mode='markers',
                    marker=dict(symbol='triangle-down', size=10, color='red'),
                    name='SELL Signal',
                    hovertext=[f"Strategy: {s} | Conf: {c:.2f}" for s, c in zip(sell_plot_data['strategy'], sell_plot_data['confidence'])],
                    hoverinfo='text'
                ))


        # Update layout
        fig.update_layout(
            title=f'{selected_symbol} Price Chart with Indicators and Signals',
            xaxis_title='Date',
            yaxis_title='Price',
            xaxis_rangeslider_visible=False,
            height=600 # Adjust height for better visibility
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write(f"No detailed data available for {selected_symbol}. Please run the analysis pipeline first.")

db.close()
