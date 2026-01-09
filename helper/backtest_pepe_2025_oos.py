import pandas as pd
import numpy as np
from binance.client import Client
import ta

# ================= CONFIG =================
SYMBOL = "SHIBUSDT"
INTERVAL = Client.KLINE_INTERVAL_4HOUR
START_DATE = "1 Jan 2024"
END_DATE   = "8 Jan 2026"

INITIAL_BALANCE = 10_000.0
RISK_PER_TRADE = 0.01
FEE_PCT = 0.001

ATR_PERIOD = 14
ATR_MULT = 2.0
# ==========================================

client = Client()


def fetch_data():
    klines = client.get_historical_klines(
        SYMBOL, INTERVAL, START_DATE, END_DATE
    )
    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "_","_","_","_","_","_"
    ])
    df = df[["time","open","high","low","close","volume"]]
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df[["open","high","low","close","volume"]] = df[
        ["open","high","low","close","volume"]
    ].astype(float)
    return df


def add_indicators(df):
    df["rsi6"] = ta.momentum.RSIIndicator(df["close"], 6).rsi()

    macd = ta.trend.MACD(df["close"])
    df["dif"] = macd.macd()
    df["dea"] = macd.macd_signal()
    df["dif_prev"] = df["dif"].shift(1)
    df["dea_prev"] = df["dea"].shift(1)

    df["atr"] = ta.volatility.AverageTrueRange(
        df["high"], df["low"], df["close"], ATR_PERIOD
    ).average_true_range()

    return df


def backtest(df):
    balance = INITIAL_BALANCE
    qty = 0.0
    entry = 0.0
    sl = 0.0
    trades = []

    for i in range(50, len(df)):
        row = df.iloc[i]

        if qty == 0:
            if (
                row["rsi6"] > 30
                and row["dif_prev"] < row["dea_prev"]
                and row["dif"] > row["dea"]
            ):
                entry = row["close"]
                sl = entry - row["atr"] * ATR_MULT
                risk_amt = balance * RISK_PER_TRADE
                qty = min(
                    risk_amt / (entry - sl),
                    balance / entry
                )
                balance -= qty * entry * FEE_PCT

        else:
            exit_price = None

            if row["low"] <= sl:
                exit_price = sl

            elif (
                row["rsi6"] < 60
                and row["dif_prev"] > row["dea_prev"]
                and row["dif"] < row["dea"]
            ):
                exit_price = row["close"]

            if exit_price:
                pnl = qty * (exit_price - entry)
                balance += pnl
                balance -= qty * exit_price * FEE_PCT
                trades.append(pnl)
                qty = 0

    return balance, trades


# ================= RUN =================
df = fetch_data()
df = add_indicators(df)

final_balance, trades = backtest(df)

wins = [t for t in trades if t > 0]

print("\n====== PEPEUSDT 2025 OUT-OF-SAMPLE ======")
print(f"Final Balance : {final_balance:.2f}")
print(f"Trades        : {len(trades)}")
print(f"Win Rate      : {len(wins)/len(trades)*100:.2f}%" if trades else "No trades")
print("=======================================\n")
