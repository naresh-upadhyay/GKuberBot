import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from binance.client import Client
import ta

# ================= CONFIG =================
SYMBOLS = ["PEPEUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT"]
INTERVAL = Client.KLINE_INTERVAL_4HOUR

LOOKBACK_MONTHS = 6
RANK_LOOKBACK = 20  # short-term momentum window

INITIAL_BALANCE = 10_000.0
RISK_PER_TRADE = 0.01
FEE_PCT = 0.001

ATR_PERIOD = 14
ATR_MULT = 2.0

MAX_OPEN_TRADES = 1
# ==========================================

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


# ================= STRATEGY BACKTEST =================
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
market = {}

print("\n===== ROLLING 6-MONTH ELIGIBILITY =====")

for sym in SYMBOLS:
    df = add_indicators(fetch_data(sym))
    market[sym] = df

    final_balance, trades, equity = backtest_single_coin(df)
    equity = np.array(equity)

    peak = np.maximum.accumulate(equity)
    max_dd = ((equity - peak) / peak).min() * 100

    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]

    avg_win = np.mean(wins) if wins else 0
    avg_loss = abs(np.mean(losses)) if losses else 1
    wl = avg_win / avg_loss if avg_loss > 0 else 0

    ret_pct = (final_balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100

    print(f"\n{sym}")
    print(f"Return : {ret_pct:.2f}%")
    print(f"Trades : {len(trades)}")
    print(f"Max DD : {max_dd:.2f}%")
    print(f"W/L    : {wl:.2f}")

    if (
        max_dd >= -15
        and len(trades) >= 25
        and wl >= 1.8
        and ret_pct >= -5
    ):
        eligible[sym] = df
        stats[sym] = {
            "long_ret": ret_pct / 100,
            "wl": wl
        }
        print("✅ ELIGIBLE")
    else:
        print("❌ DISABLED")

print("\nEligible Coins:", list(eligible.keys()))


# ================= COMPOSITE RANKING =================
def rank_coins_composite(eligible_data, stats, lookback):
    scores = {}

    for sym, df in eligible_data.items():
        if len(df) < lookback + 1:
            continue

        # short-term momentum
        short_ret = (
            df["close"].iloc[-1] - df["close"].iloc[-lookback]
        ) / df["close"].iloc[-lookback]

        long_ret = stats[sym]["long_ret"]
        wl = stats[sym]["wl"]

        score = (
            0.5 * short_ret +
            0.3 * long_ret +
            0.2 * wl
        )

        scores[sym] = score

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[0][0] if ranked else None


top_coin = rank_coins_composite(eligible, stats, RANK_LOOKBACK)

print("\n===== TOP RANKED COIN (COMPOSITE) =====")
print(top_coin)
print("=====================================\n")


# ================= FINAL PORTFOLIO =================
def trade_top_coin(df):
    balance = INITIAL_BALANCE
    qty = entry = sl = 0.0
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
                balance += qty * (exit_price - entry)
                balance -= qty * exit_price * FEE_PCT
                qty = 0

        equity.append(balance)

    equity = np.array(equity)
    peak = np.maximum.accumulate(equity)
    max_dd = ((equity - peak) / peak).min() * 100

    return balance, max_dd


# ================= RUN =================
if top_coin:
    final_balance, max_dd = trade_top_coin(eligible[top_coin])

    print("===== FINAL RESULT =====")
    print(f"Trading Coin : {top_coin}")
    print(f"Final Balance: {final_balance:.2f}")
    print(f"Max Drawdown : {max_dd:.2f}%")
    print("========================\n")
else:
    print("No eligible coin to trade.")
