import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests # NEW: for making HTTP requests (Discord)
import os 

# 1. PAGE SETUP
st.set_page_config(layout="wide", page_title="SMC Algo Trader")
st.title("🤖 Smart Money Concepts (SMC) Trader")

import requests # Make sure this import is at the top of your file
# ... other imports ...

# 2. DISCORD NOTIFICATION FUNCTION (Reads secret key)
def send_discord_alert(message):
    try:
        # Use .get() to safely retrieve the secret, returning None if not found
        WEBHOOK_URL = st.secrets.get("DISCORD_WEBHOOK_URL")

        if not WEBHOOK_URL:
            # If the secret is missing, show a clear error and exit the function
            st.error("Error: The 'DISCORD_WEBHOOK_URL' secret is not configured in Streamlit Cloud.")
            return

        payload = {
            "content": message,
            "username": "SMC Trading Bot"
        }
        
        # Send the POST request to the Webhook URL
        requests.post(WEBHOOK_URL, json=payload)
        
    except Exception as e:
        # We print to the Streamlit logs, but don't stop the app
        print(f"Failed to send Discord alert. Check secret key: {e}")

# 3. SIDEBAR CONTROLS
st.sidebar.header("Market Settings")
symbol = st.sidebar.text_input("Symbol", value="BTC/USDT")
timeframe = st.sidebar.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1)

# 4. FUNCTION TO FETCH DATA (Connects to Binance)
def get_data(symbol, timeframe):
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=500)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df = df.set_index('time')
    return df

# 5. CUSTOM SMC LOGIC: BASIC ORDER BLOCK DETECTION
def find_order_blocks(df, lookback=1):
    df['up_move'] = df['close'] > df['close'].shift(1)
    df['down_candle'] = df['close'] < df['open']
    
    order_blocks = []
    
    for i in range(1, len(df) - lookback):
        # Look for a bearish candle followed by a strong bullish move
        if df['down_candle'].iloc[i] and all(df['up_move'].iloc[i+1 : i+1+lookback]):
            ob_low = df['low'].iloc[i]
            ob_high = df['high'].iloc[i]
            ob_time = df.index[i]
            
            order_blocks.append({
                'time': ob_time,
                'low': ob_low,
                'high': ob_high
            })
            
    return pd.DataFrame(order_blocks)

# 6. MAIN APPLICATION
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
                fig.add_shape(type="rect",
                    x0=row['time'], y0=row['low'],
                    x1=df.index[-1], y1=row['high'],
                    line=dict(color="green", width=1),
                    fillcolor="green", opacity=0.2
                )
                ob_count += 1

            # Final Chart Polish
            fig.update_layout(xaxis_rangeslider_visible=False, height=600, title=f"{symbol} - Custom Order Block Analysis")
            st.plotly_chart(fig, use_container_width=True)

            # E. AI "Teacher" Insights & Alert Trigger
            st.success(f"📊 Analysis Complete! Found {ob_count} potential Bullish Order Blocks.")
            
            # 🔔 DISCORD NOTIFICATION TRIGGER
            if ob_count > 0:
                alert_message = f"🟢 ALERT: SMC Bot found {ob_count} BULLISH Order Blocks on **{symbol}-{timeframe}**. Check the dashboard now!"
                send_discord_alert(alert_message)


        except Exception as e:
            st.error(f"Error: {e}. Please check the symbol name (e.g., BTC/USDT) and refresh.")

# 7. EDUCATION SECTION
with st.expander("📚 Learn: What is an Order Block?"):
    st.write("""
    **Order Block (OB):** This is the last bearish candle (or area) before a major push higher that breaks the previous swing high. 
    Our bot highlights the low-to-high range of that candle as a zone where institutions likely placed their buy orders. 
    When price returns to this green zone, we look for a reaction.
    """)
