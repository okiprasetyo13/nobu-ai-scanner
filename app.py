
import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh

# --- UI setup ---
st.set_page_config(page_title="Nobu AI Terminal", layout="wide")
st.title("📡 Nobu AI - Multi-Timeframe Signal Scanner (M1 + M5)")

# --- Telegram Alert Function ---
def send_telegram_alert(bot_token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        requests.post(url, data=payload)
    except Exception as e:
        st.warning(f"Telegram alert failed: {e}")

# --- Binance Configuration ---
BINANCE_URL = "https://api.binance.com/api/v3/klines"
symbols = ['BTC', 'ETH', 'SOL', 'AVAX', 'LTC', 'DOGE', 'MATIC', 'ADA', 'LINK', 'OP']
binance_pairs = {s: f"{s}USDT" for s in symbols}

# --- Helper Functions ---
def preload_binance(symbol, interval='1m', limit=30):
    try:
        pair = binance_pairs[symbol]
        params = {'symbol': pair, 'interval': interval, 'limit': limit}
        r = requests.get(BINANCE_URL, params=params)
        return [[float(i[4]), float(i[5])] for i in r.json()]
    except:
        return []

def fetch_binance_price(symbol):
    try:
        pair = binance_pairs[symbol]
        url = f"https://api.binance.com/api/v3/ticker/price"
        r = requests.get(url, params={'symbol': pair})
        return float(r.json()['price'])
    except:
        return None

def plot_inline_chart(df, tp):
    fig, ax = plt.subplots(figsize=(3, 1.5))
    ax.plot(df['price'], label='Price')
    ax.plot(df['ema9'], '--', label='EMA9')
    ax.plot(df['ema21'], ':', label='EMA21')
    ax.axhline(tp, color='green', linestyle='-.', linewidth=1, label='TP')
    ax.set_xticks([]); ax.set_yticks([])
    buf = BytesIO(); plt.tight_layout(); plt.savefig(buf, format='png')
    buf.seek(0); plt.close(fig)
    return f'<img src="data:image/png;base64,{base64.b64encode(buf.read()).decode()}" width="200">'

def analyze(symbol):
    m1_data = preload_binance(symbol, interval='1m', limit=30)
    m5_data = preload_binance(symbol, interval='5m', limit=30)
    if len(m1_data) < 30 or len(m5_data) < 30:
        return {"Symbol": symbol, "Signal": "Waiting", "Chart": ""}

    df_m1 = pd.DataFrame(m1_data, columns=["price", "volume"])
    df_m1['ema9'] = EMAIndicator(close=df_m1['price'], window=9).ema_indicator()
    df_m1['ema21'] = EMAIndicator(close=df_m1['price'], window=21).ema_indicator()
    df_m1['rsi'] = RSIIndicator(close=df_m1['price'], window=14).rsi()
    df_m1['vol_spike'] = df_m1['volume'] > 1.5 * df_m1['volume'].rolling(20).mean()

    latest = df_m1.iloc[-1]
    price = latest['price']
    tp = price + 0.5
    sl = price - 0.3
    status = "In Progress"

    df_m5 = pd.DataFrame(m5_data, columns=["price", "volume"])
    df_m5['ema9'] = EMAIndicator(close=df_m5['price'], window=9).ema_indicator()
    df_m5['ema21'] = EMAIndicator(close=df_m5['price'], window=21).ema_indicator()
    df_m5['rsi'] = RSIIndicator(close=df_m5['price'], window=14).rsi()

    trend_bull = df_m5['ema9'].iloc[-1] > df_m5['ema21'].iloc[-1]
    trend_bear = df_m5['ema9'].iloc[-1] < df_m5['ema21'].iloc[-1]

    signal = "Neutral"
    score = 0

    if latest['rsi'] < 30 and latest['ema9'] > latest['ema21'] and latest['vol_spike'] and trend_bull:
        signal = "✅ Confirmed Long Entry"
        score = 4
    elif latest['rsi'] > 70 and latest['ema9'] < latest['ema21'] and latest['vol_spike'] and trend_bear:
        signal = "✅ Confirmed Short Entry"
        score = 4
    elif latest['vol_spike']:
        signal = "⚡ Volume Spike"
        score = 1

    chart_html = plot_inline_chart(df_m1[['price', 'ema9', 'ema21']], tp)

    return {
        "Symbol": symbol,
        "RSI": round(latest['rsi'], 2),
        "EMA9": round(latest['ema9'], 3),
        "EMA21": round(latest['ema21'], 3),
        "Support": round(df_m1['price'].rolling(20).min().iloc[-1], 3),
        "Resistance": round(df_m1['price'].rolling(20).max().iloc[-1], 3),
        "Volume": round(latest['volume'], 2),
        "Signal": signal,
        "Entry": round(price, 3),
        "SL": round(sl, 3),
        "TP": round(tp, 3),
        "Status": status,
        "Score": score,
        "Chart": chart_html
    }

# --- Refresh Control ---
refresh_interval = st.slider("⏱ Refresh Interval (seconds)", 5, 60, 10)
st_autorefresh(interval=refresh_interval * 1000, key="refresh")

# --- Run Analysis ---
results = [analyze(s) for s in symbols]

# --- Live Price Fetch ---
live_prices = {s: fetch_binance_price(s) for s in symbols}

# --- Display Unified Signal Table ---
columns_to_show = ["Symbol", "Price", "RSI", "EMA9", "EMA21", "Support", "Resistance",
                   "Volume", "Signal", "Entry", "SL", "TP", "Status", "Score", "Chart"]

df = pd.DataFrame(results)

# Ensure columns are filled and inject live price
for col in columns_to_show:
    if col not in df.columns:
        df[col] = None
df["Price"] = df["Symbol"].apply(lambda sym: round(live_prices.get(sym, 0) or 0, 3))

df_filtered = df.dropna(subset=columns_to_show, how='any')
st.markdown("### 📊 Signals with Live Price")
#st.write("✅ Debug: Filtered rows count = ", len(df_filtered))
#st.write("✅ Debug: Columns =", df_filtered.columns.tolist())
if not df_filtered.empty:
    st.write(df_filtered[columns_to_show].to_html(escape=False), unsafe_allow_html=True)
else:
    st.warning("⚠️ No valid signal data to display. Waiting for fresh candles...")
