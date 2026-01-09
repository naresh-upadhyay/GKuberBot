import pandas as pd
import numpy as np
from binance.client import Client
import ta

# ================= CONFIG =================
SYMBOL = "PEPEUSDT"
INTERVAL = Client.KLINE_INTERVAL_4HOUR
START_DATE = "1 Jan 2024"
END_DATE   = "1 Jan 2025"

INITIAL_BALANCE = 10_000.0
RISK_PER_TRADE = 0.01          # 1% risk
FEE_PCT = 0.001                # 0.1% spot fee

ATR_PERIOD = 14
ATR_MULT = 2.0                 # catastrophic stop
# ==========================================

client = Client()  # no API key needed


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

    # MACD
    macd = ta.trend.MACD(
        close=df["close"],
        window_slow=26,
        window_fast=12,
        window_sign=9
    )
    df["dif"] = macd.macd()
    df["dea"] = macd.macd_signal()
    df["dif_prev"] = df["dif"].shift(1)
    df["dea_prev"] = df["dea"].shift(1)

    # ATR
    df["atr"] = ta.volatility.AverageTrueRange(
        df["high"], df["low"], df["close"], ATR_PERIOD
    ).average_true_range()

    return df


# ================= BACKTEST =================
def backtest(df):
    balance = INITIAL_BALANCE
    position_qty = 0.0
    entry_price = 0.0
    stoploss = 0.0

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
                atr = row["atr"]

                stoploss = entry_price - (atr * ATR_MULT)

                risk_amount = balance * RISK_PER_TRADE
                risk_per_unit = entry_price - stoploss

                position_qty = risk_amount / risk_per_unit
                position_qty = min(position_qty, balance / entry_price)

                entry_fee = position_qty * entry_price * FEE_PCT
                balance -= entry_fee

        # ================= SELL =================
        else:
            exit_price = None

            # ATR catastrophic stop
            if row["low"] <= stoploss:
                exit_price = stoploss

            # MACD exit
            elif (
                row["rsi6"] < 60
                and row["dif_prev"] > row["dea_prev"]
                and row["dif"] < row["dea"]
            ):
                exit_price = row["close"]

            if exit_price:
                pnl = position_qty * (exit_price - entry_price)
                exit_fee = position_qty * exit_price * FEE_PCT
                net_pnl = pnl - exit_fee

                balance += net_pnl
                trades.append(net_pnl)

                position_qty = 0.0
                entry_price = 0.0
                stoploss = 0.0

    return balance, trades


# ================= RUN =================
df = fetch_data()
df = add_indicators(df)

final_balance, trades = backtest(df)

wins = [t for t in trades if t > 0]
losses = [t for t in trades if t <= 0]

print("\n====== PEPEUSDT 4H (RISK-CONTROLLED) ======")
print(f"Initial Balance : {INITIAL_BALANCE:.2f} USDT")
print(f"Final Balance   : {final_balance:.2f} USDT")
print(f"Total Trades    : {len(trades)}")

if trades:
    print(f"Win Rate        : {len(wins)/len(trades)*100:.2f}%")
    print(f"Avg Win         : {np.mean(wins):.2f} USDT" if wins else "Avg Win: 0")
    print(f"Avg Loss        : {np.mean(losses):.2f} USDT" if losses else "Avg Loss: 0")

print("==========================================\n")
