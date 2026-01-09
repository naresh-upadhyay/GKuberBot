import pandas as pd
import numpy as np
from decimal import Decimal

# ================= CONFIG =================
START_BALANCE = Decimal("10000")
RISK_PER_TRADE = Decimal("0.01")
LEVERAGE = Decimal("2")

FUNDING_LONG_THRESHOLD = Decimal("-0.0001")   # -0.01%
FUNDING_SHORT_THRESHOLD = Decimal("0.0001")   # +0.01%

STOP_ATR = Decimal("2.5")
ATR_PERIOD = 14

# ================= LOAD DATA =================
# You must export these manually from Binance or use API once
# funding.csv: time, fundingRate
# candles.csv: time, open, high, low, close

funding = pd.read_csv("funding.csv", parse_dates=["time"])
candles = pd.read_csv("candles.csv", parse_dates=["time"])

candles.set_index("time", inplace=True)
funding.set_index("time", inplace=True)

# ================= ATR =================
tr = np.maximum(
    candles["high"] - candles["low"],
    np.maximum(
        abs(candles["high"] - candles["close"].shift()),
        abs(candles["low"] - candles["close"].shift())
    )
)
candles["atr"] = tr.rolling(ATR_PERIOD).mean()

# ================= BACKTEST =================
balance = START_BALANCE
equity = START_BALANCE

in_pos = False
direction = None
entry_price = None
stop_price = None
qty = None

trades = wins = losses = 0
funding_collected = Decimal("0")

for time, row in funding.iterrows():
    if time not in candles.index:
        continue

    price = Decimal(str(candles.loc[time]["close"]))
    atr = Decimal(str(candles.loc[time]["atr"]))

    if atr.is_nan():
        continue

    rate = Decimal(str(row["fundingRate"]))

    # ================= ENTRY =================
    if not in_pos:
        risk = balance * RISK_PER_TRADE
        qty = (risk / (atr * STOP_ATR)) * LEVERAGE

        if rate <= FUNDING_LONG_THRESHOLD:
            in_pos = True
            direction = "LONG"
            entry_price = price
            stop_price = price - atr * STOP_ATR

        elif rate >= FUNDING_SHORT_THRESHOLD:
            in_pos = True
            direction = "SHORT"
            entry_price = price
            stop_price = price + atr * STOP_ATR

        continue

    # ================= FUNDING PAYMENT =================
    funding_pnl = qty * price * rate
    funding_collected += funding_pnl
    balance += funding_pnl

    # ================= EXIT =================
    if direction == "LONG":
        if price <= stop_price or rate > Decimal("0"):
            pnl = (price - entry_price) * qty
            balance += pnl
            trades += 1
            wins += 1 if pnl > 0 else 0
            losses += 1 if pnl <= 0 else 0
            in_pos = False

    if direction == "SHORT":
        if price >= stop_price or rate < Decimal("0"):
            pnl = (entry_price - price) * qty
            balance += pnl
            trades += 1
            wins += 1 if pnl > 0 else 0
            losses += 1 if pnl <= 0 else 0
            in_pos = False

# ================= REPORT =================
print("\n====== FUNDING RATE STRATEGY RESULT ======")
print(f"Trades              : {trades}")
print(f"Win Rate (%)        : {round((wins/trades)*100,2) if trades else 0}")
print(f"Funding Collected   : {round(funding_collected,2)} USDT")
print(f"Net PnL             : {round(balance - START_BALANCE,2)} USDT")
print("=========================================")
