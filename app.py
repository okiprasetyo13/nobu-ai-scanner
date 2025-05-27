import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Nobu AI Terminal", layout="wide")
st.title("📡 Nobu AI - Real-Time Scalping Signal Scanner (Azure)")

st.caption(f"Updated at: {datetime.now().strftime('%H:%M:%S')}")

BINANCE_URL = "https://api.binance.com/api/v3/klines"
symbols = ['BTC', 'ETH', 'SOL', 'AVAX', 'LTC', 'DOGE', 'MATIC', 'ADA', 'LINK', 'OP']
binance_pairs = {s: f"{s}USDT" for s in symbols}
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def fetch_klines(symbol, interval='1m', limit=30):
    pair = binance_pairs[symbol]
    params = {'symbol': pair, 'interval': interval, 'limit': limit}
    for _ in range(3):
        try:
            response = requests.get(BINANCE_URL, params=params, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if len(data) == limit:
                    df = pd.DataFrame(data, columns=[
                        "time", "open", "high", "low", "close", "volume",
                        "close_time", "qav", "trades", "tbav", "tqav", "ignore"
                    ])
                    df["close"] = pd.to_numeric(df["close"])
                    df["volume"] = pd.to_numeric(df["volume"])
                    df["time"] = pd.to_datetime(df["time"], unit="ms")
                    return df
        except Exception:
            time.sleep(0.5)
    return pd.DataFrame()

def plot_chart(df, tp):
    fig, ax = plt.subplots(figsize=(3, 1.5))
    ax.plot(df['close'], label='Price')
    ax.plot(df['ema9'], '--', label='EMA9')
    ax.plot(df['ema21'], ':', label='EMA21')
    ax.axhline(tp, color='green', linestyle='-.', linewidth=1, label='TP')
    ax.set_xticks([]); ax.set_yticks([])
    buf = BytesIO(); plt.tight_layout(); plt.savefig(buf, format='png')
    buf.seek(0); plt.close(fig)
    return f'<img src="data:image/png;base64,{base64.b64encode(buf.read()).decode()}" width="200">'

def analyze(symbol):
    m1 = fetch_klines(symbol, '1m', 30)
    m5 = fetch_klines(symbol, '5m', 30)

    if m1.empty or m5.empty:
        st.warning(f"{symbol}: Missing candles (M1={len(m1)}, M5={len(m5)})")
        return {"Symbol": symbol, "Signal": "Waiting", "Chart": "", "Valid": False}

    m1['ema9'] = EMAIndicator(close=m1['close'], window=9).ema_indicator()
    m1['ema21'] = EMAIndicator(close=m1['close'], window=21).ema_indicator()
    m1['rsi'] = RSIIndicator(close=m1['close']).rsi()
    m1['vol_spike'] = m1['volume'] > 1.5 * m1['volume'].rolling(20).mean()

    latest = m1.iloc[-1]
    tp = latest['close'] + 0.5
    sl = latest['close'] - 0.3

    m5['ema9'] = EMAIndicator(close=m5['close'], window=9).ema_indicator()
    m5['ema21'] = EMAIndicator(close=m5['close'], window=21).ema_indicator()

    trend_bull = m5['ema9'].iloc[-1] > m5['ema21'].iloc[-1]
    trend_bear = m5['ema9'].iloc[-1] < m5['ema21'].iloc[-1]

    signal = "Neutral"
    score = 0

    if latest['rsi'] < 30 and latest['ema9'] > latest['ema21'] and latest['vol_spike'] and trend_bull:
        signal = "✅ Long Entry"
        score = 4
    elif latest['rsi'] > 70 and latest['ema9'] < latest['ema21'] and latest['vol_spike'] and trend_bear:
        signal = "✅ Short Entry"
        score = 4
    elif latest['vol_spike']:
        signal = "⚡ Volume Spike"
        score = 1

    chart = plot_chart(m1, tp)
    st.success(f"{symbol}: M1 = {len(m1)}, M5 = {len(m5)}, Last = {latest['time'].strftime('%H:%M:%S')}")

    return {
        "Symbol": symbol,
        "Price": round(latest['close'], 3),
        "RSI": round(latest['rsi'], 2),
        "EMA9": round(latest['ema9'], 3),
        "EMA21": round(latest['ema21'], 3),
        "Support": round(m1['close'].rolling(20).min().iloc[-1], 3),
        "Resistance": round(m1['close'].rolling(20).max().iloc[-1], 3),
        "Volume": round(latest['volume'], 2),
        "Signal": signal,
        "Entry": round(latest['close'], 3),
        "SL": round(sl, 3),
        "TP": round(tp, 3),
        "Score": score,
        "Status": "Monitoring",
        "Time": latest['time'].strftime('%H:%M:%S'),
        "Chart": chart,
        "Valid": True
    }

refresh_seconds = st.slider("⏱ Refresh Interval", 5, 60, 10)
st_autorefresh(interval=refresh_seconds * 1000, key="refresh")
results = [analyze(s) for s in symbols]
df = pd.DataFrame([r for r in results if r["Valid"]])

if not df.empty:
    st.markdown("### ✅ Live Scalping Signals")
    st.write(df.drop(columns=["Valid"]).to_html(escape=False), unsafe_allow_html=True)
else:
    st.info("⚙️ All symbols analyzed — but no valid signal yet.")