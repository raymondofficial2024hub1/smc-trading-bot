import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests 
from smartmoneyconcepts import smc 
import numpy as np # Essential for Numba/llvmlite dependency which the SMC library uses

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="SMC Trading Bot Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. DISCORD NOTIFICATION FUNCTION (Robust Secret Handling) ---
def send_discord_alert(alert_message):
    """Sends an alert message to a configured Discord Webhook."""
    try:
        # Use .get() to safely retrieve the secret (prevents KeyError crash)
        WEBHOOK_URL = st.secrets.get("DISCORD_WEBHOOK_URL")

        if not WEBHOOK_URL:
            # If the secret is missing, show a clear error and exit the function
            st.error("🚨 Error: The 'DISCORD_WEBHOOK_URL' secret is not configured in Streamlit Cloud. Cannot send alert.")
            return

        payload = {
            "content": alert_message,
            "username": "SMC Trading Bot"
        }
        
        # Send the POST request
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 204:
            st.success("✅ Discord Alert Sent Successfully!")
        else:
            st.error(f"❌ Failed to send Discord alert. Status code: {response.status_code}. Please check the Webhook URL.")
            
    except requests.exceptions.RequestException as req_err:
        st.error(f"❌ Connection Error sending Discord alert: {req_err}")
    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {e}")


# --- 3. DATA FETCHING AND PROCESSING ---
@st.cache_data(ttl=600) # Cache data for 10 minutes
def fetch_data(ticker, period, interval):
    """Fetches OHLCV data and prepares it for SMC analysis."""
    st.info(f"Fetching {ticker} data for {period} at {interval} interval...")
    try:
        data = yf.download(ticker, period=period, interval=interval)
        if data.empty:
            return pd.DataFrame()
            
        # CRITICAL FIX: Rename columns to lowercase for smartmoneyconcepts package compatibility
        # yfinance returns 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'
        data.columns = [col.lower() for col in data.columns]
        data = data.rename(columns={'adj close': 'close'})
        
        # Ensure we have the required columns
        if not all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            st.error("Missing essential price columns after fetching and renaming.")
            return pd.DataFrame()
            
        return data

    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return pd.DataFrame()

# --- 4. SMC ANALYSIS ---
def run_smc_analysis(df):
    """Runs Smart Money Concepts analysis on the dataframe."""
    if df.empty:
        return df

    try:
        # 1. Detect Swing Highs and Lows
        df = smc.highs_lows(df, up_thresh=0.05, down_thresh=-0.05) 
        
        # 2. Detect Order Blocks (requires 'highslows' column)
        if 'highslows' in df.columns:
            df = smc.ob(df, swing_highs_lows=df['highslows'])
        else:
            st.warning("Skipping Order Block analysis: Swing Highs/Lows not detected.")

        # 3. Detect Fair Value Gaps
        df = smc.fvg(df)
        
    except Exception as e:
        st.warning(f"SMC Analysis failed with an internal error: {e}. Showing raw data.")
        # If SMC analysis fails, return the raw data frame
        return df

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
    
    # Filter the DataFrame to only show the requested lookback period for the chart
    df_chart = df_analyzed.iloc[-lookback:].copy()

    # 5. PLOT THE CHART (Candlestick)
    fig = go.Figure(data=[go.Candlestick(
        x=df_chart.index,
        open=df_chart['open'],
        high=df_chart['high'],
        low=df_chart['low'],
        close=df_chart['close'],
        name='Candlestick'
    )])

    # Basic layout updates
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
        # Get the latest close price for the alert message
        current_price = df_chart['close'].iloc[-1]
        alert_msg = f"SMC Bot Alert for {symbol.upper()} ({interval}): Current price is {current_price:.2f}. Check for new opportunities."
        send_discord_alert(alert_msg)

    st.subheader("Raw Analyzed Data (Last 5 Bars)")
    # Show the last 5 bars of the data, including the new SMC columns
    st.dataframe(df_analyzed.tail().T) 
else:
    st.warning("Could not load market data. Please check the symbol and ensure the market is open or data is available.")
