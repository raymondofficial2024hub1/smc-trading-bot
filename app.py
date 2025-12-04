import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from smartmoneyconcepts import smc

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
    # Fetch 500 candles
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=500)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    return df

# 4. MAIN LOGIC
if st.button("Analyze Market"):
    with st.spinner(f"Fetching data for {symbol}..."):
        try:
            # A. Get Data
            df = get_data(symbol, timeframe)
            
            # B. Apply SMC Logic (The "Cheat Code")
            # This detects Fair Value Gaps (FVG)
            df['FVG'] = smc.fvg(df)
            # This detects Highs and Lows
            df['HighLow'] = smc.highs_lows(df)
            # This detects Order Blocks (OB)
            df['OB'] = smc.ob(df)

            # C. Draw the Chart
            fig = go.Figure(data=[go.Candlestick(
                x=df['time'],
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                name=symbol
            )])

            # D. Draw Order Blocks on Chart
            # We filter for where Order Blocks exist and draw rectangles
            ob_data = df[df['OB'] != 0]
            if not ob_data.empty:
                for index, row in ob_data.iterrows():
                    color = "green" if row['OB'] == 1 else "red"
                    # Draw a rectangle for the Order Block
                    fig.add_shape(type="rect",
                        x0=row['time'], y0=row['low'],
                        x1=df['time'].iloc[-1], y1=row['high'],
                        line=dict(color=color, width=1),
                        fillcolor=color, opacity=0.3
                    )

            # Final Chart Polish
            fig.update_layout(xaxis_rangeslider_visible=False, height=600, title=f"{symbol} - Smart Money Analysis")
            st.plotly_chart(fig, use_container_width=True)

            # E. AI "Teacher" Insights
            st.info(f"📊 Analysis: We found {len(ob_data)} Order Blocks in the last 500 candles. "
                    "In SMC, these Green Zones are where institutions (banks) likely placed Buy Orders.")

        except Exception as e:
            st.error(f"Error: {e}. Please check the symbol name (e.g., BTC/USDT).")

# 5. EDUCATION SECTION
with st.expander("📚 Learn: What is an Order Block?"):
    st.write("""
    **Order Block (OB):** A specific price area where big banks and institutions have accumulated large orders. 
    - If price returns to a **Green OB**, we expect a bounce UP.
    - If price returns to a **Red OB**, we expect a rejection DOWN.
    """)
