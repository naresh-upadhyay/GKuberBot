import pandas as pd
import numpy as np
from binance.client import Client
import ta

# ================= CONFIG =================
SYMBOL = "PEPEUSDT"
INTERVAL = Client.KLINE_INTERVAL_4HOUR
START_DATE = "1 Jan 2025"
END_DATE   = "1 Jan 2026"

INITIAL_BALANCE = 10_000.0
FEE_PCT = 0.001        # 0.1% Binance spot fee
# ==========================================

client = Client()  # no API key needed for historical data


# ================= DATA =================
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


# ================= INDICATORS =================
def add_indicators(df):
    # RSI(6)
    df["rsi6"] = ta.momentum.RSIIndicator(
        close=df["close"], window=6
    ).rsi()

    # MACD (DIF & DEA)
    macd = ta.trend.MACD(
        close=df["close"],
        window_slow=26,
        window_fast=12,
        window_sign=9
    )
    df["dif"] = macd.macd()
    df["dea"] = macd.macd_signal()

    # Previous values for crossover detection
    df["dif_prev"] = df["dif"].shift(1)
    df["dea_prev"] = df["dea"].shift(1)

    return df


# ================= BACKTEST =================
def backtest(df):
    balance = INITIAL_BALANCE
    position_qty = 0.0
    entry_price = 0.0

    trades = []

    for i in range(50, len(df)):
        row = df.iloc[i]

        # ================= BUY =================
        if position_qty == 0:
            buy_signal = (
                row["rsi6"] > 30
                and row["dif_prev"] < row["dea_prev"]
                and row["dif"] > row["dea"]
            )

            if buy_signal:
                entry_price = row["close"]
                position_qty = balance / entry_price

                fee = position_qty * entry_price * FEE_PCT
                balance -= fee

        # ================= SELL =================
        else:
            sell_signal = (
                row["rsi6"] < 60
                and row["dif_prev"] > row["dea_prev"]
                and row["dif"] < row["dea"]
            )

            if sell_signal:
                exit_price = row["close"]

                pnl = position_qty * (exit_price - entry_price)
                fee = position_qty * exit_price * FEE_PCT
                net_pnl = pnl - fee

                balance += net_pnl
                trades.append(net_pnl)

                position_qty = 0.0
                entry_price = 0.0

    return balance, trades


# ================= RUN =================
df = fetch_data()
df = add_indicators(df)

final_balance, trades = backtest(df)

wins = [t for t in trades if t > 0]
losses = [t for t in trades if t <= 0]

print("\n========== PEPEUSDT BACKTEST (4H) ==========")
print(f"Initial Balance : {INITIAL_BALANCE:.2f} USDT")
print(f"Final Balance   : {final_balance:.2f} USDT")
print(f"Total Trades    : {len(trades)}")

if trades:
    print(f"Win Rate        : {len(wins)/len(trades)*100:.2f}%")
    print(f"Avg Win         : {np.mean(wins):.4f} USDT" if wins else "Avg Win: 0")
    print(f"Avg Loss        : {np.mean(losses):.4f} USDT" if losses else "Avg Loss: 0")
else:
    print("No trades executed")

print("===========================================\n")
