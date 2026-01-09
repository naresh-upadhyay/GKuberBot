import pandas as pd
import numpy as np
from binance.client import Client
import ta
from collections import deque

# ================= CONFIG =================
SYMBOLS = ["PEPEUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT"]
INTERVAL = Client.KLINE_INTERVAL_4HOUR
START_DATE = "1 Jan 2025"
END_DATE   = "1 Jan 2026"

INITIAL_BALANCE = 10_000.0
FEE_PCT = 0.001

ATR_PERIOD = 14
ATR_MULT = 2.0

MAX_OPEN_TRADES = 2
MAX_PORTFOLIO_RISK = 0.02  # 2% max total risk
# ==========================================

client = Client()


# ================= DATA =================
def fetch_data(symbol):
    klines = client.get_historical_klines(
        symbol, INTERVAL, START_DATE, END_DATE
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


# ================= LOAD DATA =================
market = {}
for s in SYMBOLS:
    df = fetch_data(s)
    market[s] = add_indicators(df)


# ================= DYNAMIC RISK =================
def risk_from_winrate(winrate):
    if winrate >= 0.50:
        return 0.015
    elif winrate >= 0.35:
        return 0.01
    else:
        return 0.005


# ================= BACKTEST =================
def backtest():
    balance = INITIAL_BALANCE
    equity_curve = []

    positions = {
        s: {"qty":0.0, "entry":0.0, "sl":0.0}
        for s in SYMBOLS
    }

    trade_history = {s: deque(maxlen=20) for s in SYMBOLS}

    max_len = min(len(df) for df in market.values())

    for i in range(50, max_len):
        open_trades = sum(1 for p in positions.values() if p["qty"] > 0)

        # current portfolio risk used
        portfolio_risk_used = sum(
            risk_from_winrate(
                sum(trade_history[s])/len(trade_history[s])
                if trade_history[s] else 0.35
            )
            for s, p in positions.items() if p["qty"] > 0
        )

        for sym in SYMBOLS:
            row = market[sym].iloc[i]
            pos = positions[sym]

            # ===== BUY =====
            if pos["qty"] == 0 and open_trades < MAX_OPEN_TRADES:
                buy_signal = (
                    row["rsi6"] > 30
                    and row["dif_prev"] < row["dea_prev"]
                    and row["dif"] > row["dea"]
                )

                if not buy_signal:
                    continue

                winrate = (
                    sum(trade_history[sym]) / len(trade_history[sym])
                    if trade_history[sym] else 0.35
                )

                risk_pct = risk_from_winrate(winrate)

                if portfolio_risk_used + risk_pct > MAX_PORTFOLIO_RISK:
                    continue

                entry = row["close"]
                sl = entry - row["atr"] * ATR_MULT

                risk_amt = balance * risk_pct
                qty = min(
                    risk_amt / (entry - sl),
                    balance / entry
                )

                balance -= qty * entry * FEE_PCT

                pos.update({"qty":qty, "entry":entry, "sl":sl})

            # ===== SELL =====
            elif pos["qty"] > 0:
                exit_price = None

                if row["low"] <= pos["sl"]:
                    exit_price = pos["sl"]

                elif (
                    row["rsi6"] < 60
                    and row["dif_prev"] > row["dea_prev"]
                    and row["dif"] < row["dea"]
                ):
                    exit_price = row["close"]

                if exit_price:
                    pnl = pos["qty"] * (exit_price - pos["entry"])
                    balance += pnl
                    balance -= pos["qty"] * exit_price * FEE_PCT

                    trade_history[sym].append(1 if pnl > 0 else 0)

                    pos.update({"qty":0.0,"entry":0.0,"sl":0.0})

        equity_curve.append(balance)

    return balance, equity_curve


# ================= RUN =================
final_balance, equity = backtest()

equity = np.array(equity)
peak = np.maximum.accumulate(equity)
max_dd = ((equity - peak) / peak).min() * 100

print("\n===== DYNAMIC ALLOCATION RESULT =====")
print(f"Final Balance : {final_balance:.2f}")
print(f"Max Drawdown  : {max_dd:.2f}%")
print("====================================\n")
