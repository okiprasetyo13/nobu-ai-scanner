import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Nobu AI Terminal", layout="wide")
st.title("📡 Nobu AI Terminal")
st.caption(f"✅ Streamlit app loaded at {datetime.now().strftime('%H:%M:%S')}")

BINANCE_URL = "https://api.binance.com/api/v3/klines"
symbols = ['BTC', 'ETH', 'SOL', 'AVAX', 'LTC', 'DOGE', 'MATIC', 'ADA', 'LINK', 'OP']
binance_pairs = {s: f"{s}USDT" for s in symbols}
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def fetch_klines(symbol, interval='1m', limit=100):
    pair = binance_pairs[symbol]
    params = {'symbol': pair, 'interval': interval, 'limit': limit}
    try:
        r = requests.get(BINANCE_URL, params=params, headers=HEADERS, timeout=10)
        data = r.json()
        if len(data) < 2:
            return pd.DataFrame()
        df = pd.DataFrame(data, columns=[
            "time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "trades", "tbav", "tqav", "ignore"
        ])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df["close"] = pd.to_numeric(df["close"])
        df["volume"] = pd.to_numeric(df["volume"])
        return df
    except:
        return pd.DataFrame()

def analyze_df(df):
    df['ema9'] = EMAIndicator(close=df['close'], window=9).ema_indicator()
    df['ema21'] = EMAIndicator(close=df['close'], window=21).ema_indicator()
    df['rsi'] = RSIIndicator(close=df['close']).rsi()
    df['vol_spike'] = df['volume'] > 1.5 * df['volume'].rolling(20).mean()
    df['signal'] = "Neutral"

    df.loc[
        (df['rsi'] < 30) & (df['ema9'] > df['ema21']) & df['vol_spike'],
        'signal'
    ] = "✅ Long Entry"

    df.loc[
        (df['rsi'] > 70) & (df['ema9'] < df['ema21']) & df['vol_spike'],
        'signal'
    ] = "✅ Short Entry"

    return df

def plot_chart(df):
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(df['time'], df['close'], label='Price')
    ax.plot(df['time'], df['ema9'], '--', label='EMA9')
    ax.plot(df['time'], df['ema21'], ':', label='EMA21')
    ax.legend()
    ax.set_title("Price with EMA")
    ax.grid(True)
    st.pyplot(fig)

tab1, tab2 = st.tabs(["📡 Live Scanner", "📊 Historical Data"])

with tab1:
    from time import sleep
    def analyze(symbol):
        df = fetch_klines(symbol, '1m', 30)
        if df.empty:
            return {"Symbol": symbol, "Signal": "Waiting", "Valid": False}
        df = analyze_df(df)
        latest = df.iloc[-1]
        return {
            "Symbol": symbol,
            "Price": round(latest['close'], 3),
            "RSI": round(latest['rsi'], 2),
            "EMA9": round(latest['ema9'], 3),
            "EMA21": round(latest['ema21'], 3),
            "Volume": round(latest['volume'], 2),
            "Signal": latest['signal'],
            "Time": latest['time'].strftime('%H:%M:%S'),
            "Valid": True
        }

    st_autorefresh(interval=10000, key="refresh")
    results = [analyze(s) for s in symbols]
    df_live = pd.DataFrame([r for r in results if r["Valid"]])
    if len(df_live) > 0:
        st.markdown("### ✅ Live Scalping Signals")
        st.write(df_live.drop(columns=["Valid"]))
    else:
        st.warning("⚠️ No valid signal data yet. Waiting for Binance...")

with tab2:
    st.markdown("### 📊 Historical Binance Signal Backtest")
    sel_symbol = st.selectbox("Select Symbol", symbols)
    timeframe = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"])
    candle_limit = st.slider("Candles to load", 50, 500, 100)

    hist_df = fetch_klines(sel_symbol, timeframe, candle_limit)
    if not hist_df.empty:
        hist_df = analyze_df(hist_df)
        plot_chart(hist_df)
        st.dataframe(hist_df[["time", "close", "RSI", "EMA9", "EMA21", "volume", "signal"]].tail(50))
    else:
        st.warning("❌ Unable to fetch data from Binance for this setting.")