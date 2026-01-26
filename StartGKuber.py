import os
import time
import pandas as pd
import ta
from binance.client import Client
from binance.streams import ThreadedWebsocketManager
from dotenv import load_dotenv
from utils.telegram import TelegramNotifier

# ================= ENV =================
load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

client = Client(API_KEY, API_SECRET)

# ================= CONFIG =================
SYMBOLS = ["PEPEUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT"]
INTERVAL = Client.KLINE_INTERVAL_1MINUTE

INITIAL_BALANCE = 10000.0
RISK_PER_TRADE = 0.01
FEE_PCT = 0.001
ATR_PERIOD = 14
ATR_MULT = 1.0

# ================= STATE =================
state = {
    s: {
        "df": pd.DataFrame(),
        "balance": INITIAL_BALANCE,
        "qty": 0.0,
        "entry": 0.0,
        "sl": 0.0
    }
    for s in SYMBOLS
}

notifier = TelegramNotifier()

# ================= INDICATORS =================
def add_indicators(df):
    if len(df) < ATR_PERIOD + 5:
        return df

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

# ================= TRADING =================
def buy(symbol, price, atr):
    s = state[symbol]

    s["entry"] = price
    s["sl"] = price - atr * ATR_MULT

    risk_amt = s["balance"] * RISK_PER_TRADE
    qty = min(risk_amt / (price - s["sl"]), s["balance"] / price)
    qty = round(qty, 0)

    if qty <= 0:
        return

    s["qty"] = qty
    s["balance"] -= qty * price * FEE_PCT

    notifier.send(
        f"🚀 <b>BUY</b>\n"
        f"Symbol: {symbol}\n"
        f"Price: {price:.8f}\n"
        f"SL: {s['sl']:.8f}\n"
        f"Qty: {qty}"
    )

    print(f"🟢 BUY {symbol} {qty} @ {price:.8f}")

def sell(symbol, price):
    s = state[symbol]

    pnl = s["qty"] * (price - s["entry"])
    s["balance"] += pnl
    s["balance"] -= s["qty"] * price * FEE_PCT

    notifier.send(
        f"🔴 <b>SELL</b>\n"
        f"Symbol: {symbol}\n"
        f"Price: {price:.8f}\n"
        f"PnL: {pnl:.2f}\n"
        f"Balance: {s['balance']:.2f}"
    )

    print(f"🔴 SELL {symbol} @ {price:.8f} PnL={pnl:.2f}")

    s["qty"] = 0

# ================= WS CALLBACK =================
def on_kline(msg):

    if "k" not in msg:
        return

    k = msg["k"]
    print(k["s"], k["i"], "closed =", k["x"], "price =", k["c"])

    # only closed candles
    if not k["x"]:
        return

    symbol = k["s"]
    s = state[symbol]

    candle = {
        "time": pd.to_datetime(k["t"], unit="ms"),
        "open": float(k["o"]),
        "high": float(k["h"]),
        "low": float(k["l"]),
        "close": float(k["c"]),
        "volume": float(k["v"]),
    }

    s["df"] = pd.concat(
        [s["df"], pd.DataFrame([candle])],
        ignore_index=True
    )

    s["df"] = add_indicators(s["df"])

    if len(s["df"]) < 50:
        return

    row = s["df"].iloc[-1]

    if s["qty"] == 0:
        if (
            row["rsi6"] > 30
            and row["dif_prev"] < row["dea_prev"]
            and row["dif"] > row["dea"]
        ):
            buy(symbol, row["close"], row["atr"])
    else:
        if row["low"] <= s["sl"]:
            sell(symbol, s["sl"])
        elif (
            row["rsi6"] < 60
            and row["dif_prev"] > row["dea_prev"]
            and row["dif"] < row["dea"]
        ):
            sell(symbol, row["close"])

# ================= START BOT =================
def start():
    twm = ThreadedWebsocketManager(API_KEY, API_SECRET)
    twm.start()

    for sym in SYMBOLS:
        twm.start_kline_socket(
            callback=on_kline,
            symbol=sym,
            interval=INTERVAL
        )

    print("🚀 Bot running 24×365 (Ctrl+C to stop)")

    while True:
        time.sleep(60)

if __name__ == "__main__":
    start()
