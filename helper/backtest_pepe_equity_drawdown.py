import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from binance.client import Client
import ta

# ================= CONFIG =================
SYMBOL = "PEPEUSDT"
INTERVAL = Client.KLINE_INTERVAL_4HOUR
START_DATE = "1 Jan 2025"
END_DATE   = "1 Jan 2026"

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
    equity_curve = []

    qty = 0.0
    entry = 0.0
    sl = 0.0

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
                balance += qty * (exit_price - entry)
                balance -= qty * exit_price * FEE_PCT
                qty = 0

        equity_curve.append(balance)

    return equity_curve


# ================= RUN =================
df = fetch_data()
df = add_indicators(df)

equity = backtest(df)
equity = np.array(equity)

peak = np.maximum.accumulate(equity)
drawdown = (equity - peak) / peak * 100

print(f"Max Drawdown: {drawdown.min():.2f}%")

plt.figure(figsize=(12,6))
plt.plot(equity, label="Equity Curve")
plt.title("PEPEUSDT 4H – Equity Curve")
plt.xlabel("Trades / Candles")
plt.ylabel("Balance (USDT)")
plt.legend()
plt.grid(True)
plt.show()
