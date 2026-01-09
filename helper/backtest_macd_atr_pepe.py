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

ATR_PERIOD = 14
ATR_MULTIPLIER = Decimal("3.0")

TP1_ATR = Decimal("2.0")
TP2_ATR = Decimal("4.0")
TP1_RATIO = Decimal("0.5")

RISK_PERCENT = Decimal("0.01")
FEE_RATE = Decimal("0.001")

START_BALANCE = Decimal("1000")
COOLDOWN_BARS = 20   # 20 minutes

# ================= CLIENT =================
client = Client()

# ================= HELPERS =================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

# ================= LOAD DATA =================
def load_klines(interval):
    print(interval)
    klines = client.get_historical_klines(
        SYMBOL, interval, START, END
    )
    df = pd.DataFrame(klines, columns=[
        "time","o","h","l","c","v",
        "_","_","_","_","_","_"
    ])
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df[["o","h","l","c"]] = df[["o","h","l","c"]].astype(float)
    return df[["time","o","h","l","c"]]

print("📥 Loading data...")
df15 = load_klines(Client.KLINE_INTERVAL_15MINUTE)
df1  = load_klines(Client.KLINE_INTERVAL_1MINUTE)

# ================= INDICATORS =================
# ---- 15m trend ----
df15["ema_f"] = ema(df15["c"], FAST)
df15["ema_s"] = ema(df15["c"], SLOW)
df15["dif"] = df15["ema_f"] - df15["ema_s"]
df15["dea"] = ema(df15["dif"], SIGNAL)
df15["ema200"] = ema(df15["c"], 200)

df15["trend"] = (
    (df15["dif"] > df15["dea"]) &
    (df15["c"] > df15["ema200"])
)

# ---- 1m execution ----
df1["ema_f"] = ema(df1["c"], FAST)
df1["ema_s"] = ema(df1["c"], SLOW)
df1["dif"] = df1["ema_f"] - df1["ema_s"]
df1["dea"] = ema(df1["dif"], SIGNAL)

tr = np.maximum(
    df1["h"] - df1["l"],
    np.maximum(
        abs(df1["h"] - df1["c"].shift()),
        abs(df1["l"] - df1["c"].shift())
    )
)
df1["atr"] = tr.rolling(ATR_PERIOD).mean()

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
cooldown = 0

trades = wins = losses = 0
gross_profit = Decimal("0")
gross_loss = Decimal("0")

i15 = 0

print("🚀 Starting backtest...")

for i in range(2, len(df1)):
    row = df1.iloc[i]

    if cooldown > 0:
        cooldown -= 1
        continue

    # ---- sync 15m candle ----
    while i15 + 1 < len(df15) and df15.iloc[i15 + 1]["time"] <= row["time"]:
        i15 += 1

    if i15 >= len(df15) or not df15.iloc[i15]["trend"]:
        continue

    if np.isnan(row["atr"]):
        continue

    price = Decimal(str(row["c"]))
    atr = Decimal(str(row["atr"]))

    prev1 = df1.iloc[i - 1]

    # ================= ENTRY (DIF / DEA) =================
    entry_signal = (
        prev1["dif"] <= prev1["dea"] and
        row["dif"] > row["dea"] and
        (row["dif"] - row["dea"]) > 0
    )

    if not in_pos and entry_signal:
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
        cooldown = COOLDOWN_BARS

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
        cooldown = COOLDOWN_BARS

    peak = max(peak, equity)
    max_dd = max(max_dd, (peak - equity) / peak)

# ================= REPORT =================
if gross_loss == 0:
    profit_factor = Decimal("0")
else:
    profit_factor = gross_profit / gross_loss

print("\n====== BACKTEST RESULT ======")
print(f"Trades        : {trades}")
print(f"Win Rate (%)  : {round((wins / trades) * 100, 2) if trades else 0}")
print(f"Net PnL       : {round(equity - START_BALANCE, 2)} USDT")
print(f"Max Drawdown  : {round(max_dd * 100, 2)}%")
print(f"Profit Factor : {round(profit_factor, 2)}")
print("============================")
