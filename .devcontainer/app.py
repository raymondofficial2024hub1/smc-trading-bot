import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests 
from smartmoneyconcepts import smc 
import numpy as np # Used by Numba/llvmlite dependencies

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="SMC Trading Bot Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. DISCORD NOTIFICATION FUNCTION ---
def send_discord_alert(alert_message):
    """Sends an alert message to a configured Discord Webhook."""
    try:
        # Robustly retrieve the secret (prevents crashing if not found)
        WEBHOOK_URL = st.secrets.get("DISCORD_WEBHOOK_URL")

        if not WEBHOOK_URL:
            st.error("🚨 Error: The 'DISCORD_WEBHOOK_URL' secret is not configured in Streamlit Cloud. Cannot send alert.")
            return

        payload = {
            "content": alert_message,
            "username": "SMC Trading Bot"
        }
        
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 204:
            st.success("✅ Discord Alert Sent Successfully!")
        else:
            st.error(f"❌ Failed to send Discord alert. Status code: {response.status_code}. Please check the Webhook URL.")
            
    except Exception as e:
        st.error(f"❌ An unexpected error occurred in Discord function: {e}")


# --- 3. DATA FETCHING AND PREPARATION ---
@st.cache_data(ttl=600)
def fetch_data(ticker, period, interval):
    """Fetches OHLCV data and prepares it with lowercase columns for SMC analysis."""
    st.info(f"Fetching {ticker} data...")
    try:
        data = yf.download(ticker, period=period, interval=interval)
        if data.empty:
            return pd.DataFrame()
            
        # CRITICAL SMC FIX: Rename columns to lowercase 
        data.columns = [col.lower() for col in data.columns]
        data = data.rename(columns={'adj close': 'close'})
        
        return data

    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return pd.DataFrame()

# --- 4. SMC ANALYSIS ---
def run_smc_analysis(df):
    """Runs Smart Money Concepts analysis."""
    if df.empty:
        return df
    
    try:
        # Detect Swing Highs and Lows
        df = smc.highs_lows(df, up_thresh=0.05, down_thresh=-0.05) 
        
        # Detect Order Blocks
        if 'highslows' in df.columns:
            df = smc.ob(df, swing_highs_lows=df['highslows'])
        
        # Detect Fair Value Gaps
        df = smc.fvg(df)
        
    except Exception as e:
        st.warning(f"SMC Analysis failed (library error): {e}. Showing raw data.")

    return df

# --- MAIN APP LOGIC ---
st.sidebar.header("Market Settings")
symbol = st.sidebar.text_input("Symbol", value="BTC-USD")
interval = st.sidebar.selectbox("Interval", options=["1h", "4h", "1d"], index=1)
period = st.sidebar.selectbox("Data Period", options=["1mo", "3mo", "6mo", "1y"], index=0)
lookback = st.sidebar.slider("Chart Lookback (Bars)", min_value=10, max_value=200, value=100)

st.title(f"📈 SMC Trading Bot Dashboard for {symbol.upper()}")

data_raw = fetch_data(symbol, period, interval)

if not data_raw.empty:
    df_analyzed = run_smc_analysis(data_raw)
    
    df_chart = df_analyzed.iloc[-lookback:].copy()

    # 5. PLOT THE CHART
    fig = go.Figure(data=[go.Candlestick(
        x=df_chart.index,
        open=df_chart['open'],
        high=df_chart['high'],
        low=df_chart['low'],
        close=df_chart['close'],
        name='Candlestick'
    )])

    fig.update_layout(
        title=f"{symbol.upper()} Price Action",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        xaxis_rangeslider_visible=False,
        height=700
    )

    st.plotly_chart(fig, use_container_width=True)

    # 6. ALERT BUTTON
    if st.button("🔔 Send Discord Alert (Example)"):
        current_price = df_chart['close'].iloc[-1]
        alert_msg = f"SMC Bot Alert for {symbol.upper()}: Current price is {current_price:.2f}."
        send_discord_alert(alert_msg)

    st.subheader("Raw Analyzed Data (Last 5 Bars)")
    st.dataframe(df_analyzed.tail().T) 
else:
    st.warning("Could not load market data.")
