import pandas as pd
import numpy as np
from binance.client import Client
from decimal import Decimal, getcontext

getcontext().prec = 28

# ================= CONFIG =================
SYMBOL = "PEPEUSDT"
START = "1 Jan 2024"
END   = "1 Jan 2025"

TIMEFRAME = Client.KLINE_INTERVAL_15MINUTE

EMA_TREND = 200
ATR_PERIOD = 14

RANGE_LOOKBACK = 20
RANGE_MULTIPLIER = 0.9

VOLUME_LOOKBACK = 20
VOLUME_MULTIPLIER = 1.8
VOLUME_CONFIRM_BARS = 2

ATR_MULTIPLIER = Decimal("3.0")
TP1_ATR = Decimal("2.0")
TP2_ATR = Decimal("6.0")
TP1_RATIO = Decimal("0.5")

RISK_PERCENT = Decimal("0.01")
FEE_RATE = Decimal("0.001")

START_BALANCE = Decimal("1000")

# ================= CLIENT =================
client = Client()

# ================= LOAD DATA =================
def load_klines():
    klines = client.get_historical_klines(
        SYMBOL, TIMEFRAME, START, END
    )
    df = pd.DataFrame(klines, columns=[
        "time","o","h","l","c","v",
        "_","_","_","_","_","_"
    ])
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df[["o","h","l","c","v"]] = df[["o","h","l","c","v"]].astype(float)
    return df[["time","o","h","l","c","v"]]

print("📥 Loading data...")
df = load_klines()

# ================= INDICATORS =================
df["ema200"] = df["c"].ewm(span=EMA_TREND, adjust=False).mean()

tr = np.maximum(
    df["h"] - df["l"],
    np.maximum(
        abs(df["h"] - df["c"].shift()),
        abs(df["l"] - df["c"].shift())
    )
)
df["atr"] = tr.rolling(ATR_PERIOD).mean()

df["range"] = df["h"] - df["l"]
df["avg_range"] = df["range"].rolling(RANGE_LOOKBACK).mean()
df["avg_range_long"] = df["avg_range"].rolling(100).mean()

df["avg_vol"] = df["v"].rolling(VOLUME_LOOKBACK).mean()

# ================= BACKTEST =================
balance = START_BALANCE
equity = START_BALANCE
peak = START_BALANCE
max_dd = Decimal("0")

in_pos = False
entry = Decimal("0")
qty = Decimal("0")
stop = Decimal("0")
tp1_hit = False

pending_breakout = False
breakout_index = None
range_high_at_break = None

trades = wins = losses = 0
gross_profit = Decimal("0")
gross_loss = Decimal("0")

print("🚀 Starting Breakout + Volume backtest (v4 – wick filtered)...")

for i in range(RANGE_LOOKBACK + 100, len(df)):
    row = df.iloc[i]

    if (
        np.isnan(row["atr"]) or
        np.isnan(row["avg_range"]) or
        np.isnan(row["avg_range_long"]) or
        np.isnan(row["avg_vol"])
    ):
        continue

    price = Decimal(str(row["c"]))
    atr = Decimal(str(row["atr"]))

    # ================= PHASE 1 — COMPRESSION =================
    compression = row["avg_range"] < row["avg_range_long"] * RANGE_MULTIPLIER
    min_range_ok = row["avg_range"] > row["avg_range_long"] * 0.6

    range_high = df.iloc[i - RANGE_LOOKBACK:i]["h"].max()

    # ================= PHASE 2 — BREAKOUT =================
    if (
        not in_pos and
        not pending_breakout and
        compression and
        min_range_ok and
        price > Decimal(str(range_high)) and
        row["c"] > row["ema200"]
    ):
        pending_breakout = True
        breakout_index = i
        range_high_at_break = Decimal(str(range_high))
        continue

    # ================= PHASE 3 — VOLUME + WICK CONFIRM =================
    if pending_breakout:
        if i - breakout_index > VOLUME_CONFIRM_BARS:
            pending_breakout = False
            continue

        # Candle anatomy
        body = abs(row["c"] - row["o"])
        upper_wick = row["h"] - max(row["c"], row["o"])

        strong_close = price > range_high_at_break * Decimal("1.002")
        volume_spike = row["v"] > row["avg_vol"] * VOLUME_MULTIPLIER
        wick_ok = upper_wick < body * 0.6   # 🔥 KEY FILTER

        if strong_close and volume_spike and wick_ok:
            risk = balance * RISK_PERCENT
            stop_dist = atr * ATR_MULTIPLIER
            qty = risk / stop_dist

            entry = price
            stop = entry - stop_dist
            tp1_hit = False
            in_pos = True
            pending_breakout = False
            continue

    if not in_pos:
        continue

    # ================= EXITS =================
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
        stop = entry

    # TP2
    elif tp1_hit and price >= entry + atr * TP2_ATR:
        pnl = (price - entry) * qty
        fee = price * qty * FEE_RATE
        net = pnl - fee

        balance += net
        equity += net
        trades += 1

        if net > 0:
            wins += 1
            gross_profit += net
        else:
            losses += 1
            gross_loss += abs(net)

        in_pos = False

    # STOP
    elif price <= stop:
        pnl = (price - entry) * qty
        fee = price * qty * FEE_RATE
        net = pnl - fee

        balance += net
        equity += net
        trades += 1

        if net > 0:
            wins += 1
            gross_profit += net
        else:
            losses += 1
            gross_loss += abs(net)

        in_pos = False

    peak = max(peak, equity)
    max_dd = max(max_dd, (peak - equity) / peak)

# ================= REPORT =================
profit_factor = gross_profit / gross_loss if gross_loss > 0 else Decimal("0")

print("\n====== BREAKOUT + VOLUME BACKTEST RESULT (v4) ======")
print(f"Trades        : {trades}")
print(f"Win Rate (%)  : {round((wins / trades) * 100, 2) if trades else 0}")
print(f"Net PnL       : {round(equity - START_BALANCE, 2)} USDT")
print(f"Max Drawdown  : {round(max_dd * 100, 2)}%")
print(f"Profit Factor : {round(profit_factor, 2)}")
print("===================================================")
