import os, json, threading
import pandas as pd
import ta
import websocket
from binance.client import Client
from dotenv import load_dotenv

from utils.telegram import TelegramNotifier

# ================= ENV =================
load_dotenv()
client = Client(
    os.getenv("BINANCE_API_KEY"),
    os.getenv("BINANCE_API_SECRET")
)

# ================= CONFIG =================
SYMBOLS = ["PEPEUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT"]
INTERVAL = Client.KLINE_INTERVAL_4HOUR

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
    } for s in SYMBOLS
}


notifier = TelegramNotifier()
# ================= INDICATORS =================
def add_indicators(df):
    if df is None or len(df) < ATR_PERIOD:
        return None  # not enough data, skip symbol
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
    qty = min(
        risk_amt / (price - s["sl"]),
        s["balance"] / price
    )

    qty = round(qty, 0)
    if qty <= 0:
        return

    #client.order_market_buy(symbol=symbol, quantity=qty)
    s["qty"] = qty
    s["balance"] -= qty * price * FEE_PCT
    notifier.send(
        f"🚀 <b>BUY</b>\n"
        f"Symbol: {symbol}\n"
        f"SL: {s["sl"]}\n"
        f"Price: {price:.8f}\n"
        f"Qty: {qty}"
    )

    print(f"🟢 {symbol} BUY {qty} @ {price:.8f}")

def sell(symbol, price):
    s = state[symbol]
    #client.order_market_sell(symbol=symbol, quantity=s["qty"])

    pnl = s["qty"] * (price - s["entry"])
    s["balance"] += pnl
    s["balance"] -= s["qty"] * price * FEE_PCT

    notifier.send(
        f"🔴 <b>SELL</b>\n"
        f"Symbol: {symbol}\n"
        f"Balance: {s["balance"]:.8f}\n"
        f"Price: {price:.8f}\n"
        f"PnL: {pnl:.2f}"
    )

    print(f"🔴 {symbol} SELL @ {price:.8f} PnL={pnl:.2f}")
    s["qty"] = 0

# ================= WS HANDLER =================
def start_socket(symbol):
    socket = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_{INTERVAL}"

    def on_message(ws, msg):
        msg = json.loads(msg)

        # Ignore non-kline messages
        if 'e' not in msg or msg['e'] != 'kline':
            return

        k = msg['k']
        print(k)
        if not k["x"]:
            return

        candle = {
            "time": pd.to_datetime(k["t"], unit="ms"),
            "open": float(k["o"]),
            "high": float(k["h"]),
            "low": float(k["l"]),
            "close": float(k["c"]),
            "volume": float(k["v"])
        }

        s = state[symbol]
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
                row["rsi6"] > 30 and
                row["dif_prev"] < row["dea_prev"] and
                row["dif"] > row["dea"]
            ):
                buy(symbol, row["close"], row["atr"])

        else:
            if row["low"] <= s["sl"]:
                sell(symbol, s["sl"])

            elif (
                row["rsi6"] < 60 and
                row["dif_prev"] > row["dea_prev"] and
                row["dif"] < row["dea"]
            ):
                sell(symbol, row["close"])

    ws = websocket.WebSocketApp(socket, on_message=on_message)
    ws.run_forever()

# ================= START ALL =================
for sym in SYMBOLS:
    threading.Thread(target=start_socket, args=(sym,), daemon=True).start()

input("🚀 Multi-pair bot running. Press ENTER to stop\n")
