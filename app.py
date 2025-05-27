import streamlit as st
import requests
import pandas as pd
from ta.momentum import RSIIndicator

st.set_page_config(page_title="Nobu AI Terminal", layout="wide")
st.title("📡 Nobu AI - Multi-Timeframe Signal Scanner (Live)")

symbols = ['OPUSDT', 'SOLUSDT', 'ETHUSDT']

def fetch_binance_klines(symbol, interval, limit=100):
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["close"] = pd.to_numeric(df["close"])
    return df

signals = []

for symbol in symbols:
    m1_df = fetch_binance_klines(symbol, "1m", 50)
    m5_df = fetch_binance_klines(symbol, "5m", 50)

    rsi_m1 = RSIIndicator(m1_df["close"]).rsi().iloc[-1]
    rsi_m5 = RSIIndicator(m5_df["close"]).rsi().iloc[-1]

    signal = "BUY" if rsi_m1 < 30 and rsi_m5 < 50 else "WAIT"

    signals.append({
        "Symbol": symbol,
        "M1 RSI": round(rsi_m1, 2),
        "M5 RSI": round(rsi_m5, 2),
        "Signal": signal
    })

df_signals = pd.DataFrame(signals)
st.dataframe(df_signals)