import pandas as pd
import numpy as np
from binance.client import Client
import ta
import matplotlib.pyplot as plt

# ===================== CONFIG =====================
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
INTERVAL = Client.KLINE_INTERVAL_1HOUR
START_DATE = "1 Jan 2024"
END_DATE = "1 Jan 2025"

INITIAL_BALANCE = 10000.0
RISK_PER_TRADE = 0.005
FEE_PCT = 0.001

ATR_PERIOD = 14
ATR_MULT = 1.5

ADX_PERIOD = 14
ADX_MIN = 25

MAX_OPEN_TRADES = 2
COOLDOWN_CANDLES = 5
MIN_CANDLES = 200
USE_BTC_REGIME_FILTER = True
USE_RSI_FILTER = True

# ==================================================

client = Client()


# ===================== DATA =====================
def fetch_data(symbol):
    klines = client.get_historical_klines(
        symbol, INTERVAL, START_DATE, END_DATE
    )

    df = pd.DataFrame(klines, columns=[
        "time", "open", "high", "low", "close", "volume",
        "_", "_", "_", "_", "_", "_"
    ])

    df = df[["time", "open", "high", "low", "close", "volume"]]
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df[["open", "high", "low", "close", "volume"]] = df[
        ["open", "high", "low", "close", "volume"]
    ].astype(float)

    return df


def add_indicators(df):
    df["ema20"] = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()
    df["ema50"] = ta.trend.EMAIndicator(df["close"], 50).ema_indicator()
    df["ema200"] = ta.trend.EMAIndicator(df["close"], 200).ema_indicator()

    df["rsi"] = ta.momentum.RSIIndicator(df["close"], 14).rsi()
    df["rsi_prev"] = df["rsi"].shift(1)

    df["vol_ma"] = df["volume"].rolling(20).mean()

    df["atr"] = ta.volatility.AverageTrueRange(
        df["high"], df["low"], df["close"], ATR_PERIOD
    ).average_true_range()

    df["adx"] = ta.trend.ADXIndicator(
        df["high"], df["low"], df["close"], ADX_PERIOD
    ).adx()

    return df


# ===================== LOAD DATA =====================
market = {}
for s in SYMBOLS:
    df = fetch_data(s)
    df = add_indicators(df)
    market[s] = df

btc_df = market["BTCUSDT"]


# ===================== BACKTEST =====================
def portfolio_backtest(data):
    balance = INITIAL_BALANCE
    equity_curve = []

    positions = {
        s: {"qty": 0.0, "entry": 0.0, "sl": 0.0, "cooldown": 0}
        for s in SYMBOLS
    }

    trades = []

    max_len = min(len(df) for df in data.values())

    for i in range(MIN_CANDLES, max_len):
        btc_row = btc_df.iloc[i]
        btc_bull = (not USE_BTC_REGIME_FILTER) or (btc_row["close"] > btc_row["ema200"])

        open_trades = sum(1 for p in positions.values() if p["qty"] > 0)

        for symbol in SYMBOLS:
            row = data[symbol].iloc[i]
            pos = positions[symbol]

            # cooldown
            if pos["cooldown"] > 0:
                pos["cooldown"] -= 1
                continue

            # ================= ENTRY =================
            if pos["qty"] == 0:
                if (
                    btc_bull
                    and open_trades < MAX_OPEN_TRADES
                    and row["ema20"] > row["ema50"]
                    and row["volume"] > row["vol_ma"]
                    and row["adx"] > ADX_MIN
                    and (not USE_RSI_FILTER or row["rsi_prev"] < 50 <= row["rsi"])
                ):
                    entry = row["close"]
                    atr = row["atr"]
                    sl = entry - (atr * ATR_MULT)

                    risk_amt = balance * RISK_PER_TRADE
                    qty = risk_amt / (entry - sl)
                    qty = min(qty, balance / entry)

                    fee = qty * entry * FEE_PCT
                    balance -= fee

                    pos.update({"qty": qty, "entry": entry, "sl": sl})
                    open_trades += 1

            # ================= TRAILING + EXIT =================
            else:
                atr = row["atr"]
                pos["sl"] = max(pos["sl"], row["close"] - atr * ATR_MULT)

                if row["low"] <= pos["sl"]:
                    exit_price = pos["sl"]
                    pnl = pos["qty"] * (exit_price - pos["entry"])
                    fee = pos["qty"] * exit_price * FEE_PCT
                    net = pnl - fee

                    balance += net
                    trades.append(net)

                    pos.update({
                        "qty": 0.0,
                        "entry": 0.0,
                        "sl": 0.0,
                        "cooldown": COOLDOWN_CANDLES
                    })

        equity_curve.append(balance)

    return balance, trades, equity_curve


# ===================== RUN =====================
final_balance, trades, equity_curve = portfolio_backtest(market)

# ===================== METRICS =====================
equity = np.array(equity_curve)
peak = np.maximum.accumulate(equity)
drawdown = (equity - peak) / peak
max_dd = drawdown.min() * 100

wins = [t for t in trades if t > 0]
losses = [t for t in trades if t <= 0]

print("\n========== FINAL PROFESSIONAL RESULT ==========")
print(f"Symbols          : {', '.join(SYMBOLS)}")
print(f"Initial Balance  : {INITIAL_BALANCE:.2f}")
print(f"Final Balance    : {final_balance:.2f}")
print(f"Total Trades     : {len(trades)}")
print(f"Win Rate         : {len(wins)/len(trades)*100:.2f}%")
print(f"Max Drawdown     : {max_dd:.2f}%")
print("==============================================\n")

# ===================== PLOT =====================
plt.figure(figsize=(12,6))
plt.plot(equity_curve, label="Equity Curve")
plt.title("Portfolio Equity Curve")
plt.xlabel("Trades")
plt.ylabel("Balance (USDT)")
plt.legend()
plt.grid(True)
plt.show()
