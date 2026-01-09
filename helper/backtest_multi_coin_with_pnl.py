import pandas as pd
import numpy as np
from binance.client import Client
import ta

# ================= CONFIG =================
SYMBOLS = ["PEPEUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT"]
INTERVAL = Client.KLINE_INTERVAL_4HOUR
START_DATE = "1 Jan 2023"
END_DATE   = "1 Jan 2024"

INITIAL_BALANCE = 10_000.0
RISK_PER_TRADE = 0.01
FEE_PCT = 0.001

ATR_PERIOD = 14
ATR_MULT = 2.0

MAX_OPEN_TRADES = 2
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
for sym in SYMBOLS:
    df = fetch_data(sym)
    market[sym] = add_indicators(df)


# ================= BACKTEST =================
def backtest():
    balance = INITIAL_BALANCE
    equity_curve = []

    positions = {
        s: {"qty": 0.0, "entry": 0.0, "sl": 0.0}
        for s in SYMBOLS
    }

    trade_log = []  # <-- for per-coin analytics

    max_len = min(len(df) for df in market.values())

    for i in range(50, max_len):
        open_trades = sum(1 for p in positions.values() if p["qty"] > 0)

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

                if buy_signal:
                    entry = row["close"]
                    sl = entry - row["atr"] * ATR_MULT

                    risk_amt = balance * RISK_PER_TRADE
                    qty = min(
                        risk_amt / (entry - sl),
                        balance / entry
                    )

                    balance -= qty * entry * FEE_PCT

                    pos.update({"qty": qty, "entry": entry, "sl": sl})

            # ===== SELL =====
            elif pos["qty"] > 0:
                exit_price = None
                reason = None

                if row["low"] <= pos["sl"]:
                    exit_price = pos["sl"]
                    reason = "SL"

                elif (
                    row["rsi6"] < 60
                    and row["dif_prev"] > row["dea_prev"]
                    and row["dif"] < row["dea"]
                ):
                    exit_price = row["close"]
                    reason = "MACD"

                if exit_price:
                    pnl = pos["qty"] * (exit_price - pos["entry"])
                    balance += pnl
                    balance -= pos["qty"] * exit_price * FEE_PCT

                    trade_log.append({
                        "symbol": sym,
                        "pnl": pnl,
                        "exit_reason": reason
                    })

                    pos.update({"qty": 0.0, "entry": 0.0, "sl": 0.0})

        equity_curve.append(balance)

    return balance, trade_log, equity_curve


# ================= RUN =================
final_balance, trades, equity = backtest()

df_trades = pd.DataFrame(trades)

print("\n===== MULTI-COIN RESULT =====")
print(f"Final Balance : {final_balance:.2f}")
print(f"Total Trades  : {len(trades)}")

equity = np.array(equity)
peak = np.maximum.accumulate(equity)
max_dd = ((equity - peak) / peak).min() * 100
print(f"Max Drawdown  : {max_dd:.2f}%")
print("================================\n")


# ================= PER-COIN ANALYTICS =================
print("===== PER-COIN PERFORMANCE =====")

for sym in SYMBOLS:
    coin_trades = df_trades[df_trades["symbol"] == sym]

    if len(coin_trades) == 0:
        print(f"{sym}: No trades")
        continue

    wins = coin_trades[coin_trades["pnl"] > 0]
    losses = coin_trades[coin_trades["pnl"] <= 0]

    print(f"\n{sym}")
    print(f"Trades     : {len(coin_trades)}")
    print(f"Total PnL  : {coin_trades['pnl'].sum():.2f}")
    print(f"Win Rate   : {len(wins)/len(coin_trades)*100:.2f}%")
    print(f"Avg Win    : {wins['pnl'].mean():.2f}" if len(wins) else "Avg Win: 0")
    print(f"Avg Loss   : {losses['pnl'].mean():.2f}" if len(losses) else "Avg Loss: 0")

print("\n================================")
