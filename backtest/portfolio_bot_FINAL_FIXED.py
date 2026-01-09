import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from binance.client import Client
import ta

# ================= CONFIG =================
SYMBOLS = ["PEPEUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT", "GUNUSDT"]
INTERVAL = Client.KLINE_INTERVAL_4HOUR

LOOKBACK_MONTHS = 1
RANK_LOOKBACK = 20

INITIAL_BALANCE = 10_000.0
RISK_PER_TRADE = 0.01
FEE_PCT = 0.001

ATR_PERIOD = 14
ATR_MULT = 1.0
# =========================================

client = Client()

END_DATE = datetime.now(timezone.utc)
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


# ================= STRATEGY =================
def backtest_single_coin(df):
    balance = INITIAL_BALANCE
    qty = entry = sl = 0.0
    trades = []
    equity = []

    for i in range(50, len(df)):
        row = df.iloc[i]

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


# ================= ELIGIBILITY =================
eligible = {}
stats = {}

print("\n===== ROLLING 6-MONTH ELIGIBILITY =====")

for sym in SYMBOLS:
    df = add_indicators(fetch_data(sym))

    final_balance, trades, equity = backtest_single_coin(df)
    equity = np.array(equity)

    peak = np.maximum.accumulate(equity)
    max_dd = ((equity - peak) / peak).min() * 100

    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]

    avg_win = np.mean(wins) if wins else 0
    avg_loss = abs(np.mean(losses)) if losses else 1
    wl = avg_win / avg_loss

    ret_pct = (final_balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100

    # ================= PROFIT REPORT =================
    profit = final_balance - INITIAL_BALANCE
    profit_pct = (profit / INITIAL_BALANCE) * 100

    print("\n===== PROFIT SUMMARY =====")
    print(f"{sym}")
    print(f"Initial Balance : {INITIAL_BALANCE:.2f} USDT")
    print(f"Final Balance   : {final_balance:.2f} USDT")

    if profit >= 0:
        print(f"Net Profit      : +{profit:.2f} USDT ({profit_pct:.2f}%)")
    else:
        print(f"Net Loss        : {profit:.2f} USDT ({profit_pct:.2f}%)")
    print(f"Return : {ret_pct:.2f}%")
    print(f"Trades : {len(trades)}")
    print(f"Max DD : {max_dd:.2f}%")
    print(f"W/L    : {wl:.2f}")
    print("==========================\n")

    if (
        #max_dd >= -15  and
        wl >= 1.8
        and ret_pct >= 0
    ):
        eligible[sym] = df
        stats[sym] = {
            "long_ret": ret_pct / 100,
            "wl_score": min(wl / 3.0, 1.0)
        }
        print("✅ ELIGIBLE")
    else:
        print("❌ DISABLED")

print("\nEligible Coins:", list(eligible.keys()))


# ================= RANKING =================
def rank_coins_fixed(eligible_data, stats, lookback):
    scores = {}

    for sym, df in eligible_data.items():
        short_ret = (
            df["close"].iloc[-1] - df["close"].iloc[-lookback]
        ) / df["close"].iloc[-lookback]

        score = (
            0.5 * stats[sym]["long_ret"] +
            0.3 * short_ret +
            0.2 * stats[sym]["wl_score"]
        )

        scores[sym] = score

    return max(scores, key=scores.get)


top_coin = rank_coins_fixed(eligible, stats, RANK_LOOKBACK)

print("\n===== TOP RANKED COIN (FINAL) =====")
print(top_coin)
print("=================================\n")
