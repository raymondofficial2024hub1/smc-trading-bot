import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. PAGE SETUP
st.set_page_config(layout="wide", page_title="SMC Algo Trader")
st.title("🤖 Smart Money Concepts (SMC) Trader")

# 2. SIDEBAR CONTROLS
st.sidebar.header("Market Settings")
symbol = st.sidebar.text_input("Symbol", value="BTC/USDT")
timeframe = st.sidebar.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1)

# 3. FUNCTION TO FETCH DATA (Connects to Binance)
def get_data(symbol, timeframe):
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=500)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df = df.set_index('time')
    return df

# 4. CUSTOM SMC LOGIC: BASIC ORDER BLOCK DETECTION
def find_order_blocks(df, lookback=1):
    # Detects the last bearish (down) candle before a strong bullish (up) movement
    # 'up_move' is true if the current candle closes higher than the previous one
    df['up_move'] = df['close'] > df['close'].shift(1)
    
    # 'down_candle' is true if the current candle closes lower than it opened
    df['down_candle'] = df['close'] < df['open']
    
    # An OB is a down candle (down_candle=True) followed by a strong up move
    # We look for a down candle followed by several consecutive up moves (lookback)
    
    order_blocks = []
    
    for i in range(1, len(df) - lookback):
        if df['down_candle'].iloc[i] and all(df['up_move'].iloc[i+1 : i+1+lookback]):
            # The low and high of the bearish candle define the OB zone
            ob_low = df['low'].iloc[i]
            ob_high = df['high'].iloc[i]
            ob_time = df.index[i]
            
            order_blocks.append({
                'time': ob_time,
                'low': ob_low,
                'high': ob_high
            })
            
    return pd.DataFrame(order_blocks)

# 5. MAIN APPLICATION
if st.button("Analyze Market"):
    with st.spinner(f"Fetching data for {symbol}..."):
        try:
            # A. Get Data
            df = get_data(symbol, timeframe)
            
            # B. Apply Custom SMC Logic
            ob_df = find_order_blocks(df)

            # C. Draw the Chart
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                name=symbol
            )])

            # D. Draw Order Blocks on Chart
            ob_count = 0
            
            for index, row in ob_df.iterrows():
                # Draw a rectangle for the Order Block
                fig.add_shape(type="rect",
                    x0=row['time'], y0=row['low'],
                    x1=df.index[-1], y1=row['high'], # Extends the box to the end of the chart
                    line=dict(color="green", width=1),
                    fillcolor="green", opacity=0.2
                )
                ob_count += 1

            # Final Chart Polish
            fig.update_layout(xaxis_rangeslider_visible=False, height=600, title=f"{symbol} - Custom Order Block Analysis")
            st.plotly_chart(fig, use_container_width=True)

            # E. AI "Teacher" Insights (Simple Version)
            st.success(f"📊 Analysis Complete! Found {ob_count} potential Bullish Order Blocks. "
                       "These green zones are high-interest areas where price may reverse UP.")

        except Exception as e:
            st.error(f"Error: {e}. Please check the symbol name (e.g., BTC/USDT) and refresh.")

# 6. EDUCATION SECTION
with st.expander("📚 Learn: What is an Order Block?"):
    st.write("""
    **Order Block (OB):** This is the last bearish candle (or area) before a major push higher that breaks the previous swing high. 
    Our bot highlights the low-to-high range of that candle as a zone where institutions likely placed their buy orders. 
    When price returns to this green zone, we look for a reaction.
    """)
