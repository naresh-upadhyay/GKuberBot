import pandas as pd
import numpy as np
from binance.client import Client
from decimal import Decimal, getcontext

getcontext().prec = 28

# ================= CONFIG =================
SYMBOL = "PEPEUSDT"
START = "1 Jan 2024"
END   = "1 Jan 2025"

FAST = 12
SLOW = 26
SIGNAL = 9

EMA_TREND = 200
ATR_PERIOD = 14

ATR_MULTIPLIER = Decimal("3.0")
TP1_ATR = Decimal("2.0")
TP2_ATR = Decimal("4.0")
TP1_RATIO = Decimal("0.5")

RISK_PERCENT = Decimal("0.01")
FEE_RATE = Decimal("0.001")

START_BALANCE = Decimal("1000")

# ================= CLIENT =================
client = Client()

# ================= HELPERS =================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

# ================= LOAD DATA =================
def load_klines():
    klines = client.get_historical_klines(
        SYMBOL,
        Client.KLINE_INTERVAL_15MINUTE,
        START,
        END
    )
    df = pd.DataFrame(klines, columns=[
        "time","o","h","l","c","v",
        "_","_","_","_","_","_"
    ])
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df[["o","h","l","c"]] = df[["o","h","l","c"]].astype(float)
    return df[["time","o","h","l","c"]]

print("📥 Loading 15m data...")
df = load_klines()

# ================= INDICATORS =================
df["ema_fast"] = ema(df["c"], FAST)
df["ema_slow"] = ema(df["c"], SLOW)
df["dif"] = df["ema_fast"] - df["ema_slow"]
df["dea"] = ema(df["dif"], SIGNAL)
df["ema200"] = ema(df["c"], EMA_TREND)

tr = np.maximum(
    df["h"] - df["l"],
    np.maximum(
        abs(df["h"] - df["c"].shift()),
        abs(df["l"] - df["c"].shift())
    )
)
df["atr"] = tr.rolling(ATR_PERIOD).mean()

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

trades = wins = losses = 0
gross_profit = Decimal("0")
gross_loss = Decimal("0")

print("🚀 Starting 15m swing backtest...")

for i in range(2, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i - 1]

    if np.isnan(row["atr"]):
        continue

    price = Decimal(str(row["c"]))
    atr = Decimal(str(row["atr"]))

    # ================= ENTRY =================
    entry_signal = (
        not in_pos and
        prev["dif"] <= prev["dea"] and
        row["dif"] > row["dea"] and
        row["dif"] > 0 and
        row["dea"] > 0 and
        row["c"] > row["ema200"]
    )

    if entry_signal:
        risk = balance * RISK_PERCENT
        stop_dist = atr * ATR_MULTIPLIER
        qty = risk / stop_dist

        entry = price
        stop = entry - stop_dist
        tp1_hit = False
        in_pos = True
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
        stop = entry  # breakeven

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

    # MACD EXIT
    elif prev["dif"] >= prev["dea"] and row["dif"] < row["dea"]:
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

    # STOP LOSS
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
profit_factor = (
    gross_profit / gross_loss
    if gross_loss > 0 else Decimal("0")
)

print("\n====== 15m SWING BACKTEST RESULT ======")
print(f"Trades        : {trades}")
print(f"Win Rate (%)  : {round((wins / trades) * 100, 2) if trades else 0}")
print(f"Net PnL       : {round(equity - START_BALANCE, 2)} USDT")
print(f"Max Drawdown  : {round(max_dd * 100, 2)}%")
print(f"Profit Factor : {round(profit_factor, 2)}")
print("======================================")
