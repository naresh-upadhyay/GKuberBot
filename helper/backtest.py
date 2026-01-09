import pandas as pd
import numpy as np
from binance.client import Client
from decimal import Decimal
from datetime import datetime

# ---------------- CONFIG ----------------
SYMBOL = "PEPEUSDT"
START = "1 Jan 2024"
END = "1 Jan 2025"

FAST, SLOW, SIGNAL = 12, 26, 9
ATR_PERIOD = 14
ATR_MULTIPLIER = Decimal("2.5")

TP1_ATR = Decimal("1.5")
TP2_ATR = Decimal("3.0")
TP1_RATIO = Decimal("0.5")

FEE_RATE = Decimal("0.001")
RISK_PERCENT = Decimal("0.01")
START_BALANCE = Decimal("1000")

# ---------------- BINANCE CLIENT ----------------
client = Client()  # public data only

# ---------------- HELPERS ----------------
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

# ---------------- LOAD DATA ----------------
def load_klines(interval):
    print(interval)
    print("load_klines")
    klines = client.get_historical_klines(
        SYMBOL, interval, START, END
    )
    print(klines)
    df = pd.DataFrame(klines, columns=[
        "time","o","h","l","c","v",
        "_","_","_","_","_","_"
    ])
    print(df)
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df[["o","h","l","c"]] = df[["o","h","l","c"]].astype(float)
    return df[["time","o","h","l","c"]]

df15 = load_klines(Client.KLINE_INTERVAL_15MINUTE)
df1  = load_klines(Client.KLINE_INTERVAL_1MINUTE)

# ---------------- INDICATORS ----------------
print("INDICATORS")
df15["ema_f"] = ema(df15["c"], FAST)
df15["ema_s"] = ema(df15["c"], SLOW)
df15["dif"] = df15["ema_f"] - df15["ema_s"]
df15["dea"] = ema(df15["dif"], SIGNAL)
df15["trend"] = (df15["dif"] > df15["dea"])

df1["ema_f"] = ema(df1["c"], FAST)
df1["ema_s"] = ema(df1["c"], SLOW)
df1["dif"] = df1["ema_f"] - df1["ema_s"]
df1["dea"] = ema(df1["dif"], SIGNAL)

# ATR
print("ATR")
tr = np.maximum(
    df1["h"] - df1["l"],
    np.maximum(
        abs(df1["h"] - df1["c"].shift()),
        abs(df1["l"] - df1["c"].shift())
    )
)
df1["atr"] = tr.rolling(ATR_PERIOD).mean()

# ---------------- BACKTEST ENGINE ----------------
print("BACKTEST")
balance = START_BALANCE
equity = START_BALANCE
peak = START_BALANCE
max_dd = Decimal("0")

in_pos = False
entry = Decimal("0")
qty = Decimal("0")
trail = Decimal("0")
tp1_hit = False

trades = wins = losses = 0
gross_profit = Decimal("0")
gross_loss = Decimal("0")

i15 = 0

for i in range(len(df1)):
    row = df1.iloc[i]
    print(row)
    # Sync 15m candle
    while i15 + 1 < len(df15) and df15.iloc[i15 + 1]["time"] <= row["time"]:
        i15 += 1

    if i15 >= len(df15) or not df15.iloc[i15]["trend"]:
        continue

    if np.isnan(row["atr"]):
        continue

    price = Decimal(str(row["c"]))
    atr = Decimal(str(row["atr"]))

    # ENTRY
    if (
        not in_pos and
        df1.iloc[i-1]["dif"] < df1.iloc[i-1]["dea"] and
        row["dif"] > row["dea"]
    ):
        risk = balance * RISK_PERCENT
        stop_dist = atr * ATR_MULTIPLIER
        qty = risk / stop_dist
        entry = price
        trail = entry - stop_dist
        tp1_hit = False
        in_pos = True
        continue

    if not in_pos:
        continue

    # TP1
    if not tp1_hit and price >= entry + atr * TP1_ATR:
        sell_qty = qty * TP1_RATIO
        pnl = (price - entry) * sell_qty
        fee = price * sell_qty * FEE_RATE
        net = pnl - fee
        balance += net
        equity += net
        qty -= sell_qty
        tp1_hit = True
        trail = entry

    # TP2
    elif tp1_hit and price >= entry + atr * TP2_ATR:
        pnl = (price - entry) * qty
        fee = price * qty * FEE_RATE
        net = pnl - fee
        balance += net
        equity += net
        trades += 1
        wins += 1 if net > 0 else 0
        losses += 1 if net <= 0 else 0
        gross_profit += max(net, 0)
        gross_loss += abs(min(net, 0))
        in_pos = False

    # STOP
    elif price <= trail:
        pnl = (price - entry) * qty
        fee = price * qty * FEE_RATE
        net = pnl - fee
        balance += net
        equity += net
        trades += 1
        wins += 1 if net > 0 else 0
        losses += 1 if net <= 0 else 0
        gross_profit += max(net, 0)
        gross_loss += abs(min(net, 0))
        in_pos = False

    peak = max(peak, equity)
    max_dd = max(max_dd, (peak - equity) / peak)

# ---------------- REPORT ----------------
profit_factor = (
    gross_profit / gross_loss if gross_loss > 0 else Decimal("inf")
)

print("\n====== BACKTEST RESULT ======")
print(f"Trades        : {trades}")
print(f"Win Rate (%)  : {round(wins / trades * 100, 2) if trades else 0}")
print(f"Net PnL       : {round(equity - START_BALANCE, 2)} USDT")
print(f"Max Drawdown  : {round(max_dd * 100, 2)}%")
print(f"Profit Factor : {round(profit_factor, 2)}")
print("============================")
