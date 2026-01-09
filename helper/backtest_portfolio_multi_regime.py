import pandas as pd
import numpy as np
from binance.client import Client
import ta

# ===================== CONFIG =====================
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
INTERVAL = Client.KLINE_INTERVAL_1HOUR
START_DATE = "1 Jan 2023"
END_DATE   = "1 Jan 2025"

INITIAL_BALANCE = 10_000.0
FEE_PCT = 0.001

MAX_OPEN_TRADES = 2
COOLDOWN = 3

# ---- Trend Strategy ----
TREND_RISK = 0.005
TREND_ADX_MIN = 20
TREND_ATR_MULT = 2.5

# ---- Range Strategy ----
RANGE_RISK = 0.003
RANGE_ADX_MAX = 20
RANGE_ATR_MULT = 1.2
VWAP_DIST = 0.002     # 0.2%

ATR_PERIOD = 14
# ==================================================

client = Client()

# ===================== DATA =====================
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
    df["ema20"] = ta.trend.EMAIndicator(df["close"],20).ema_indicator()
    df["ema50"] = ta.trend.EMAIndicator(df["close"],50).ema_indicator()
    df["ema200"] = ta.trend.EMAIndicator(df["close"],200).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"],14).rsi()
    df["adx"] = ta.trend.ADXIndicator(
        df["high"],df["low"],df["close"],14
    ).adx()
    df["atr"] = ta.volatility.AverageTrueRange(
        df["high"],df["low"],df["close"],ATR_PERIOD
    ).average_true_range()
    df["vwap"] = (df["volume"] * df["close"]).cumsum() / df["volume"].cumsum()
    return df

market = {}
for s in SYMBOLS:
    df = fetch_data(s)
    market[s] = add_indicators(df)

btc_df = market["BTCUSDT"]

# ===================== BACKTEST =====================
def backtest():
    balance = INITIAL_BALANCE
    equity_curve = []

    positions = {
        s: {"qty":0,"entry":0,"sl":0,"cool":0}
        for s in SYMBOLS
    }

    trades = []

    max_len = min(len(df) for df in market.values())

    for i in range(200, max_len):
        btc = btc_df.iloc[i]
        btc_bull = btc["close"] > btc["ema200"]

        open_trades = sum(1 for p in positions.values() if p["qty"] > 0)

        for sym in SYMBOLS:
            row = market[sym].iloc[i]
            pos = positions[sym]

            if pos["cool"] > 0:
                pos["cool"] -= 1
                continue

            # ================= ENTRY =================
            if pos["qty"] == 0 and open_trades < MAX_OPEN_TRADES:

                # ---- TREND MODE ----
                if (
                    btc_bull
                    and row["ema20"] > row["ema50"]
                    and row["adx"] >= TREND_ADX_MIN
                ):
                    risk = balance * TREND_RISK
                    sl = row["close"] - row["atr"] * TREND_ATR_MULT
                    qty = min(risk / (row["close"] - sl), balance / row["close"])

                # ---- RANGE MODE ----
                elif (
                    row["adx"] < RANGE_ADX_MAX
                    and abs(row["close"] - row["vwap"]) / row["close"] < VWAP_DIST
                    and 40 <= row["rsi"] <= 60
                ):
                    risk = balance * RANGE_RISK
                    sl = row["close"] - row["atr"] * RANGE_ATR_MULT
                    qty = min(risk / (row["close"] - sl), balance / row["close"])

                else:
                    continue

                fee = qty * row["close"] * FEE_PCT
                balance -= fee

                pos.update({
                    "qty": qty,
                    "entry": row["close"],
                    "sl": sl
                })

            # ================= EXIT =================
            else:
                # trailing stop
                new_sl = row["close"] - row["atr"] * (
                    TREND_ATR_MULT if btc_bull else RANGE_ATR_MULT
                )
                pos["sl"] = max(pos["sl"], new_sl)

                if row["low"] <= pos["sl"]:
                    exit_price = pos["sl"]
                    pnl = pos["qty"] * (exit_price - pos["entry"])
                    fee = pos["qty"] * exit_price * FEE_PCT
                    net = pnl - fee

                    balance += net
                    trades.append(net)

                    pos.update({"qty":0,"entry":0,"sl":0,"cool":COOLDOWN})

        equity_curve.append(balance)

    return balance, trades, equity_curve

# ===================== RUN =====================
final_balance, trades, equity = backtest()

equity = np.array(equity)
peak = np.maximum.accumulate(equity)
dd = ((equity - peak) / peak).min() * 100

wins = [t for t in trades if t > 0]

print("\n===== MULTI-REGIME RESULT =====")
print(f"Final Balance : {final_balance:.2f}")
print(f"Trades        : {len(trades)}")
print(f"Win Rate      : {len(wins)/len(trades)*100:.2f}%" if trades else "No trades")
print(f"Max Drawdown  : {dd:.2f}%")
print("================================\n")
