import pandas as pd
import numpy as np
from binance.client import Client
from decimal import Decimal, getcontext

getcontext().prec = 28

# ================= CONFIG =================
SYMBOL = "BTCUSDT"
START = "1 Jan 2024"
END   = "1 Jan 2025"

TIMEFRAME = Client.KLINE_INTERVAL_15MINUTE

VWAP_LOOKBACK = 96        # ~1 day
ATR_PERIOD = 14

VWAP_DEV_ATR = 1.2        # 🔧 relaxed
WICK_RATIO = 0.8          # 🔧 relaxed

RISK_PERCENT = Decimal("0.01")
FEE_RATE = Decimal("0.001")

START_BALANCE = Decimal("10000")

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

print("📥 Loading BTC data...")
df = load_klines()

# ================= INDICATORS =================
# VWAP
tp = (df["h"] + df["l"] + df["c"]) / 3
df["vwap"] = (tp * df["v"]).rolling(VWAP_LOOKBACK).sum() / df["v"].rolling(VWAP_LOOKBACK).sum()

# ATR
tr = np.maximum(
    df["h"] - df["l"],
    np.maximum(
        abs(df["h"] - df["c"].shift()),
        abs(df["l"] - df["c"].shift())
    )
)
df["atr"] = tr.rolling(ATR_PERIOD).mean()

# Value area low proxy (instead of sweep)
df["value_low"] = df["c"].rolling(VWAP_LOOKBACK).quantile(0.2)

# ================= BACKTEST =================
balance = START_BALANCE
equity = START_BALANCE
peak = START_BALANCE
max_dd = Decimal("0")

in_pos = False
entry = Decimal("0")
qty = Decimal("0")
stop = Decimal("0")

trades = wins = losses = 0
gross_profit = Decimal("0")
gross_loss = Decimal("0")

print("🚀 Starting Mean Reversion VWAP backtest (v2)...")

for i in range(VWAP_LOOKBACK + 2, len(df)):
    row = df.iloc[i]

    if np.isnan(row["vwap"]) or np.isnan(row["atr"]) or np.isnan(row["value_low"]):
        continue

    price = Decimal(str(row["c"]))
    atr = Decimal(str(row["atr"]))
    vwap = Decimal(str(row["vwap"]))

    # ================= ENTRY =================
    body = abs(row["c"] - row["o"])
    lower_wick = min(row["c"], row["o"]) - row["l"]

    deep_below_vwap = price < vwap - Decimal(str(VWAP_DEV_ATR * row["atr"]))
    value_extension = price < Decimal(str(row["value_low"]))
    wick_reject = lower_wick > body * WICK_RATIO

    entry_signal = (
        not in_pos and
        deep_below_vwap and
        value_extension and
        wick_reject
    )

    if entry_signal:
        risk = balance * RISK_PERCENT
        stop_dist = atr * Decimal("1.2")
        qty = risk / stop_dist

        entry = price
        stop = price - stop_dist
        in_pos = True
        continue

    if not in_pos:
        continue

    # ================= EXIT =================
    # TP at VWAP
    if price >= vwap:
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

    # Stop
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

print("\n====== MEAN REVERSION VWAP BACKTEST RESULT (v2) ======")
print(f"Trades        : {trades}")
print(f"Win Rate (%)  : {round((wins / trades) * 100, 2) if trades else 0}")
print(f"Net PnL       : {round(equity - START_BALANCE, 2)} USDT")
print(f"Max Drawdown  : {round(max_dd * 100, 2)}%")
print(f"Profit Factor : {round(profit_factor, 2)}")
print("=====================================================")
