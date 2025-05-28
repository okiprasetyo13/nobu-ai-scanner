import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import time

st.set_page_config(page_title="Nobu AI Terminal – Elite Scalping", layout="wide")
st.title("📡 Nobu AI Terminal – Elite Crypto Scalping (Coinbase)")

COINBASE_URL = "https://api.exchange.coinbase.com"
products = ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LTC-USD", "MATIC-USD", "OP-USD"]
intervals = {
    "1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400
}

def fetch_candles(symbol, granularity, limit=100):
    try:
        url = f"{COINBASE_URL}/products/{symbol}/candles"
        params = {"granularity": granularity}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if not isinstance(data, list) or len(data) == 0:
            return pd.DataFrame()
        df = pd.DataFrame(data, columns=["time", "low", "high", "open", "close", "volume"])
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.sort_values("time", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
    except Exception as e:
        return pd.DataFrame()

def fetch_live_price(symbol):
    try:
        url = f"{COINBASE_URL}/products/{symbol}/ticker"
        r = requests.get(url, timeout=5)
        return float(r.json().get("price", 0))
    except:
        return 0

def analyze(df):
    df["ema9"] = EMAIndicator(close=df["close"], window=9).ema_indicator()
    df["ema21"] = EMAIndicator(close=df["close"], window=21).ema_indicator()
    df["rsi"] = RSIIndicator(close=df["close"]).rsi()
    df["support"] = df["low"].rolling(20).min()
    df["resistance"] = df["high"].rolling(20).max()
    df["signal"] = "Neutral"
    df["score"] = 0

    signal_cond = (
        (df["rsi"] < 35) &
        (df["ema9"] > df["ema21"]) &
        (df["volume"] > df["volume"].rolling(20).mean())
    )
    df.loc[signal_cond, "signal"] = "✅ Long"
    df.loc[signal_cond, "score"] = 4

    return df

def mini_chart(df):
    fig, ax = plt.subplots(figsize=(2.5, 1.5))
    ax.plot(df["close"], label="Close", linewidth=1)
    ax.plot(df["ema9"], '--', label="EMA9", linewidth=0.8)
    ax.plot(df["ema21"], ':', label="EMA21", linewidth=0.8)
    ax.set_xticks([]); ax.set_yticks([])
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    return f'<img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}" width="160">'

selected_interval = st.selectbox("Select Timeframe", list(intervals.keys()), index=0)
granularity = intervals[selected_interval]

results = []

for symbol in products:
    df = fetch_candles(symbol, granularity)
    if df.empty or len(df) < 30:
        continue
    df = analyze(df)
    last = df.iloc[-1]
    entry = last["close"]
    support = last["support"]
    resistance = last["resistance"]
    sl = round(support - (entry - support)*0.5, 2)
    tp = round(entry + (resistance - entry)*0.5, 2)
    chart = mini_chart(df)
    live_price = fetch_live_price(symbol)
    results.append({
        "Symbol": f"{symbol} (${round(live_price, 2)})",
        "Signal": last["signal"],
        "Score": last["score"],
        "RSI": round(last["rsi"], 2),
        "EMA9": round(last["ema9"], 2),
        "EMA21": round(last["ema21"], 2),
        "Support": round(support, 2),
        "Resistance": round(resistance, 2),
        "Buy Price": round(entry, 2),
        "SL": sl,
        "TP": tp,
        "Chart": chart
    })

st.markdown("### 📊 Expert Scalping Signal Table")

if results:
    df_result = pd.DataFrame(results)
    st.write(df_result.to_html(escape=False), unsafe_allow_html=True)
else:
    st.warning("⚠️ No valid signal data yet. Try a different timeframe or wait for updates.")