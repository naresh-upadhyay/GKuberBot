import pandas as pd
import numpy as np
from binance.client import Client
import ta

# ===================== CONFIG =====================
SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_15MINUTE
START_DATE = "1 Jan 2024"
END_DATE = "1 Jan 2025"

INITIAL_BALANCE = 10_000.0
RISK_PER_TRADE = 0.01        # 1% risk per trade
FEE_PCT = 0.001              # 0.1% Binance spot fee

ATR_PERIOD = 14
SL_ATR_MULT = 1.5            # Stop loss = ATR * 1.5
TP_ATR_MULT = 3.0            # Take profit = ATR * 3

MIN_CANDLES = 50
# ==================================================

client = Client()  # No API key needed


# ===================== DATA =====================
def fetch_data():
    klines = client.get_historical_klines(
        SYMBOL, INTERVAL, START_DATE, END_DATE
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
    df["vol_ma"] = df["volume"].rolling(20).mean()

    df["atr"] = ta.volatility.AverageTrueRange(
        df["high"], df["low"], df["close"], ATR_PERIOD
    ).average_true_range()

    return df


# ===================== BACKTEST =====================
def backtest(df):
    balance = INITIAL_BALANCE
    position_qty = 0.0
    entry_price = 0.0
    stoploss = 0.0
    takeprofit = 0.0

    trades = []
    equity_curve = []

    for i in range(MIN_CANDLES, len(df)):
        row = df.iloc[i]

        # ========== ENTRY ==========
        if position_qty == 0:
            if (
                row["ema20"] > row["ema50"]
                and row["volume"] > row["vol_ma"]
                and 40 < row["rsi"] < 70
            ):
                entry_price = row["close"]
                atr = row["atr"]

                stoploss = entry_price - (atr * SL_ATR_MULT)
                takeprofit = entry_price + (atr * TP_ATR_MULT)

                risk_amount = balance * RISK_PER_TRADE
                risk_per_unit = entry_price - stoploss

                position_qty = risk_amount / risk_per_unit

                # Safety: cannot exceed balance
                max_qty = balance / entry_price
                position_qty = min(position_qty, max_qty)

                entry_fee = position_qty * entry_price * FEE_PCT
                balance -= entry_fee

        # ========== EXIT ==========
        else:
            exit_price = None

            if row["low"] <= stoploss:
                exit_price = stoploss
            elif row["high"] >= takeprofit:
                exit_price = takeprofit

            if exit_price:
                pnl = position_qty * (exit_price - entry_price)
                exit_fee = position_qty * exit_price * FEE_PCT
                net_pnl = pnl - exit_fee

                balance += net_pnl
                trades.append(net_pnl)

                position_qty = 0.0
                entry_price = 0.0

        equity_curve.append(balance)

    return balance, trades, equity_curve


# ===================== RUN =====================
df = fetch_data()
df = add_indicators(df)

final_balance, trades, equity_curve = backtest(df)

wins = [t for t in trades if t > 0]
losses = [t for t in trades if t <= 0]

print("\n========== ATR BACKTEST RESULT ==========")
print(f"Symbol           : {SYMBOL}")
print(f"Initial Balance  : {INITIAL_BALANCE:.2f} USDT")
print(f"Final Balance    : {final_balance:.2f} USDT")
print(f"Total Trades     : {len(trades)}")

if trades:
    print(f"Win Rate         : {len(wins) / len(trades) * 100:.2f}%")
    print(f"Average Win      : {np.mean(wins):.2f} USDT" if wins else "Average Win      : 0")
    print(f"Average Loss     : {np.mean(losses):.2f} USDT" if losses else "Average Loss     : 0")
else:
    print("No trades executed")

print("========================================\n")

assert not np.isnan(final_balance)
assert not np.isinf(final_balance)
