import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from binance.client import Client
import ta

# ================= CONFIG =================
SYMBOLS = ["PEPEUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT"]
INTERVAL = Client.KLINE_INTERVAL_4HOUR

LOOKBACK_MONTHS = 6

INITIAL_BALANCE = 10_000.0
RISK_PER_TRADE = 0.01
FEE_PCT = 0.001

ATR_PERIOD = 14
ATR_MULT = 2.0
# ==========================================

client = Client()


# ================= DATE RANGE =================
END_DATE = datetime.utcnow()
START_DATE = END_DATE - timedelta(days=LOOKBACK_MONTHS * 30)


# ================= DATA =================
def fetch_data(symbol):
    klines = client.get_historical_klines(
        symbol,
        INTERVAL,
        START_DATE.strftime("%d %b %Y"),
        END_DATE.strftime("%d %b %Y")
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


# ================= STRATEGY BACKTEST =================
def backtest_single_coin(df):
    balance = INITIAL_BALANCE
    qty = 0.0
    entry = 0.0
    sl = 0.0

    trades = []
    equity = []

    for i in range(50, len(df)):
        row = df.iloc[i]

        # BUY
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

        # SELL
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
                pnl = qty * (exit_price - entry)
                balance += pnl
                balance -= qty * exit_price * FEE_PCT
                trades.append(pnl)
                qty = 0

        equity.append(balance)

    return balance, trades, equity


# ================= ELIGIBILITY CHECK =================
eligible = []

print("\n===== ROLLING 6-MONTH ELIGIBILITY =====")

for sym in SYMBOLS:
    df = add_indicators(fetch_data(sym))

    if len(df) < 100:
        print(f"{sym}: ❌ Not enough data")
        continue

    final_balance, trades, equity = backtest_single_coin(df)

    equity = np.array(equity)
    peak = np.maximum.accumulate(equity)
    max_dd = ((equity - peak) / peak).min() * 100

    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]

    avg_win = np.mean(wins) if wins else 0
    avg_loss = abs(np.mean(losses)) if losses else 1

    ret_pct = (final_balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100

    print(f"\n{sym}")
    print(f"Return     : {ret_pct:.2f}%")
    print(f"Trades     : {len(trades)}")
    print(f"Max DD     : {max_dd:.2f}%")
    print(f"Win/Loss   : {avg_win/avg_loss:.2f}")

    if (
        max_dd >= -15
        and len(trades) >= 25
        and avg_win / avg_loss >= 1.8
        and ret_pct >= -5
    ):
        eligible.append(sym)
        print("✅ ELIGIBLE")
    else:
        print("❌ DISABLED")

print("\n===== FINAL ELIGIBLE COINS =====")
print(eligible)
print("================================\n")
