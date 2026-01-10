import os
import json
import pandas as pd
import ta
import websocket
from binance.client import Client
from dotenv import load_dotenv

# ================= LOAD ENV =================
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# ================= CONFIG =================
SYMBOL = "PEPEUSDT"
INTERVAL = Client.KLINE_INTERVAL_1SECOND
#INTERVAL = Client.KLINE_INTERVAL_4HOUR
SOCKET = f"wss://stream.binance.com:9443/ws/{SYMBOL.lower()}@kline_{INTERVAL}"

INITIAL_BALANCE = 10_000.0
RISK_PER_TRADE = 0.01
FEE_PCT = 0.001

ATR_PERIOD = 14
ATR_MULT = 1.0

# ================= CLIENT =================
client = Client(API_KEY, API_SECRET)

# ================= STATE =================
df = pd.DataFrame()
balance = INITIAL_BALANCE
qty = 0.0
entry = 0.0
sl = 0.0

# ================= HELPERS =================
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

def place_buy(price, atr):
    global qty, entry, sl, balance

    entry = price
    sl = entry - atr * ATR_MULT

    risk_amt = balance * RISK_PER_TRADE
    qty = min(
        risk_amt / (entry - sl),
        balance / entry
    )

    qty = round(qty, 0)  # PEPE integer qty

    if qty <= 0:
        return

    #client.order_market_buy(symbol=SYMBOL, quantity=qty)
    balance -= qty * entry * FEE_PCT

    print(f"🟢 BUY {qty} @ {entry:.8f} SL={sl:.8f}")

def place_sell(price):
    global qty, balance, entry

    #client.order_market_sell(symbol=SYMBOL, quantity=qty)

    pnl = qty * (price - entry)
    balance += pnl
    balance -= qty * price * FEE_PCT

    print(f"🔴 SELL {qty} @ {price:.8f} PnL={pnl:.2f} Bal={balance:.2f}")

    qty = 0

# ================= WS CALLBACK =================
def on_message(ws, message):
    global df, qty

    msg = json.loads(message)
    k = msg["k"]

    # Only CLOSED candle
    if not k["x"]:
        return

    candle = {
        "time": pd.to_datetime(k["t"], unit="ms"),
        "open": float(k["o"]),
        "high": float(k["h"]),
        "low": float(k["l"]),
        "close": float(k["c"]),
        "volume": float(k["v"]),
    }

    df = pd.concat([df, pd.DataFrame([candle])], ignore_index=True)
    df = add_indicators(df)

    if len(df) < 50:
        return

    row = df.iloc[-1]

    # ===== ENTRY =====
    if qty == 0:
        if (
            row["rsi6"] > 30
            and row["dif_prev"] < row["dea_prev"]
            and row["dif"] > row["dea"]
        ):
            place_buy(row["close"], row["atr"])

    # ===== EXIT =====
    else:
        if row["low"] <= sl:
            place_sell(sl)

        elif (
            row["rsi6"] < 60
            and row["dif_prev"] > row["dea_prev"]
            and row["dif"] < row["dea"]
        ):
            place_sell(row["close"])

def on_open(ws):
    print("✅ WebSocket Connected")

def on_error(ws, error):
    print("❌ WS Error:", error)

def on_close(ws):
    print("🔌 WebSocket Closed")

# ================= START =================
ws = websocket.WebSocketApp(
    SOCKET,
    on_message=on_message,
    on_open=on_open,
    on_error=on_error,
    on_close=on_close
)

ws.run_forever()
