import pandas as pd
import numpy as np
from binance.client import Client
import ta

# ===================== CONFIG =====================
SYMBOLS = ["PEPEUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT"]
INTERVAL = Client.KLINE_INTERVAL_1HOUR
START_DATE = "1 Jan 2023"
END_DATE = "1 Jan 2024"

INITIAL_BALANCE = 10000.0
RISK_PER_TRADE = 0.005          # 0.5% risk
FEE_PCT = 0.001                 # spot fee

ATR_PERIOD = 14
SL_ATR_MULT = 1.5
TP_ATR_MULT = 3.0

ADX_PERIOD = 14
ADX_MIN = 25

COOLDOWN_CANDLES = 5
MIN_CANDLES = 100
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


# ===================== INDICATORS =====================
def add_indicators(df):
    df["ema20"] = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()
    df["ema50"] = ta.trend.EMAIndicator(df["close"], 50).ema_indicator()

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


# ===================== LOAD ALL SYMBOLS =====================
market_data = {}

for symbol in SYMBOLS:
    df = fetch_data(symbol)
    df = add_indicators(df)
    market_data[symbol] = df


# ===================== BACKTEST =====================
def portfolio_backtest(data):
    balance = INITIAL_BALANCE

    positions = {
        s: {
            "qty": 0.0,
            "entry": 0.0,
            "sl": 0.0,
            "tp": 0.0,
            "cooldown": 0
        } for s in SYMBOLS
    }

    trades = []
    equity_curve = []

    # assume all data aligned by index (1H candles)
    max_len = min(len(df) for df in data.values())

    for i in range(MIN_CANDLES, max_len):
        for symbol in SYMBOLS:
            row = data[symbol].iloc[i]
            pos = positions[symbol]

            # ===== cooldown =====
            if pos["cooldown"] > 0:
                pos["cooldown"] -= 1
                continue

            # ===== ENTRY =====
            if pos["qty"] == 0:
                if (
                    row["ema20"] > row["ema50"]
                    and row["volume"] > row["vol_ma"]
                    and row["adx"] > ADX_MIN
                    and row["rsi_prev"] < 50 <= row["rsi"]
                ):
                    entry = row["close"]
                    atr = row["atr"]

                    sl = entry - (atr * SL_ATR_MULT)
                    tp = entry + (atr * TP_ATR_MULT)

                    risk_amount = balance * RISK_PER_TRADE
                    risk_per_unit = entry - sl
                    qty = risk_amount / risk_per_unit

                    max_qty = balance / entry
                    qty = min(qty, max_qty)

                    fee = qty * entry * FEE_PCT
                    balance -= fee

                    pos.update({
                        "qty": qty,
                        "entry": entry,
                        "sl": sl,
                        "tp": tp
                    })

            # ===== EXIT =====
            else:
                exit_price = None

                if row["low"] <= pos["sl"]:
                    exit_price = pos["sl"]
                elif row["high"] >= pos["tp"]:
                    exit_price = pos["tp"]

                if exit_price:
                    pnl = pos["qty"] * (exit_price - pos["entry"])
                    fee = pos["qty"] * exit_price * FEE_PCT
                    net_pnl = pnl - fee

                    balance += net_pnl
                    trades.append(net_pnl)

                    pos.update({
                        "qty": 0.0,
                        "entry": 0.0,
                        "sl": 0.0,
                        "tp": 0.0,
                        "cooldown": COOLDOWN_CANDLES
                    })

        equity_curve.append(balance)

    return balance, trades, equity_curve


# ===================== RUN =====================
final_balance, trades, equity_curve = portfolio_backtest(market_data)

wins = [t for t in trades if t > 0]
losses = [t for t in trades if t <= 0]

print("\n========== PORTFOLIO BACKTEST RESULT ==========")
print(f"Symbols          : {', '.join(SYMBOLS)}")
print(f"Timeframe        : 1H")
print(f"Initial Balance  : {INITIAL_BALANCE:.2f} USDT")
print(f"Final Balance    : {final_balance:.2f} USDT")
print(f"Total Trades     : {len(trades)}")

if trades:
    print(f"Win Rate         : {len(wins) / len(trades) * 100:.2f}%")
    print(f"Average Win      : {np.mean(wins):.2f} USDT" if wins else "Average Win      : 0")
    print(f"Average Loss     : {np.mean(losses):.2f} USDT" if losses else "Average Loss     : 0")
else:
    print("No trades executed")

print("==============================================\n")

assert not np.isnan(final_balance)
assert not np.isinf(final_balance)
