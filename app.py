import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

st.set_page_config(page_title="Nobu AI Terminal - Coinbase Pro", layout="wide")
st.title("📡 Nobu AI Terminal - Expert Scalping (Coinbase)")

COINBASE_URL = "https://api.exchange.coinbase.com"
products = ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LTC-USD", "MATIC-USD", "OP-USD"]

intervals = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400
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
        df = df.sort_values("time")
        df.reset_index(drop=True, inplace=True)
        return df
    except:
        return pd.DataFrame()

def analyze(df):
    df["ema9"] = EMAIndicator(close=df["close"], window=9).ema_indicator()
    df["ema21"] = EMAIndicator(close=df["close"], window=21).ema_indicator()
    df["rsi"] = RSIIndicator(close=df["close"]).rsi()
    df["support"] = df["low"].rolling(20).min()
    df["resistance"] = df["high"].rolling(20).max()
    df["signal"] = "Neutral"
    df["score"] = 0

    conditions = (
        (df["rsi"] < 30) &
        (df["ema9"] > df["ema21"]) &
        (df["volume"] > df["volume"].rolling(20).mean())
    )
    df.loc[conditions, "signal"] = "✅ Long"
    df.loc[conditions, "score"] = 4

    return df

def mini_chart(df):
    fig, ax = plt.subplots(figsize=(2.5, 1.5))
    ax.plot(df["close"], label="Close")
    ax.plot(df["ema9"], '--', label="EMA9")
    ax.plot(df["ema21"], ':', label="EMA21")
    ax.set_xticks([]); ax.set_yticks([])
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    return f'<img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}" width="180">'

selected_interval = st.selectbox("Select Timeframe", list(intervals.keys()), index=0)
granularity = intervals[selected_interval]

result_rows = []

for symbol in products:
    df = fetch_candles(symbol, granularity, limit=100)
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

    result_rows.append({
        "Symbol": symbol,
        "Buy Price": round(entry, 2),
        "Support": round(support, 2),
        "Resistance": round(resistance, 2),
        "SL": sl,
        "TP": tp,
        "Score": last["score"],
        "Signal": last["signal"],
        "Chart": chart
    })

if result_rows:
    df_result = pd.DataFrame(result_rows)
    st.markdown("### 📈 Expert-Level Scalping Signals (Coinbase)")
    st.write(df_result.to_html(escape=False), unsafe_allow_html=True)
else:
    st.warning("⚠️ No valid signal data yet. Please try a different timeframe or wait for new candles.")