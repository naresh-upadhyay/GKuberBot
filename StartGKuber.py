
"""from utils.telegram import TelegramNotifier

notifier = TelegramNotifier()

notifier.send(
    f"🚀 <b>BUY</b>\n"
    f"Symbol: BTCUSDT\n"
    f"Entry: 42350\n"
    f"SL: 41920\n"
    f"TP: 43210\n"
    f"Qty: 0.012"
)


https://api.binance.com
https://api-gcp.binance.com
https://api1.binance.com
https://api2.binance.com
https://api3.binance.com
https://api4.binance.com

Key	Value
apiKey	vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A
secretKey	NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j

Example of request with a symbol name comprised entirely of ASCII characters:
Parameter	Value
symbol	LTCBTC
side	BUY
type	LIMIT
timeInForce	GTC
quantity	1
price	0.1
recvWindow	5000
timestamp	1499827319559
curl -s -v -H "X-MBX-APIKEY: $apiKey" -X POST "https://api.binance.com/api/v3/order?symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559&signature=c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71"

Example of request with a symbol name comprised entirely of ASCII characters:

Parameter	Value
symbol	BTCUSDT
side	SELL
type	LIMIT
timeInForce	GTC
quantity	1
price	0.2
timestamp	1668481559918
recvWindow	5000


"""

import json
import websocket
import threading
from datetime import datetime

# ---- SOCKETS ----
SOCKET_15M = "wss://stream.binance.com:9443/ws/pepeusdt@kline_15m"
SOCKET_1M  = "wss://stream.binance.com:9443/ws/pepeusdt@kline_1m"

# ---- MACD SETTINGS ----
FAST = 7
SLOW = 25
SIGNAL = 9

# ---- ATR ----
ATR_PERIOD = 14
ATR_MULTIPLIER = 2.5

# ---- 15m STATE (TREND) ----
ema_fast_15 = ema_slow_15 = dea_15 = None
prev_dif_15 = prev_dea_15 = None
trend_bullish = False

# ---- 1m STATE (ENTRY) ----
ema_fast_1 = ema_slow_1 = dea_1 = None
prev_dif_1 = prev_dea_1 = None

atr = None
prev_close = None

in_position = False
entry_price = None
trailing_sl = None

# ---- HELPERS ----
def ema(val, prev, period):
    k = 2 / (period + 1)
    return val if prev is None else val * k + prev * (1 - k)

def update_atr(high, low, close):
    global atr, prev_close
    if prev_close is None:
        prev_close = close
        return None
    tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
    atr = tr if atr is None else (atr * (ATR_PERIOD - 1) + tr) / ATR_PERIOD
    prev_close = close
    return atr

# ---- 15m HANDLER (TREND FILTER) ----
def on_15m(ws, msg):
    global ema_fast_15, ema_slow_15, dea_15
    global prev_dif_15, prev_dea_15, trend_bullish

    k = json.loads(msg)['k']
    if not k['x']:
        return

    close = float(k['c'])
    time = datetime.fromtimestamp(k['T'] / 1000)

    ema_fast_15 = ema(close, ema_fast_15, FAST)
    ema_slow_15 = ema(close, ema_slow_15, SLOW)

    dif = ema_fast_15 - ema_slow_15
    dea_15 = ema(dif, dea_15, SIGNAL)
    hist = dif - dea_15

    if prev_dif_15 is not None:
        trend_bullish = dif > dea_15 and hist > 0

    prev_dif_15, prev_dea_15 = dif, dea_15

    print(f"[15m] {time} DIF:{dif:.8f} DEA:{dea_15:.8f} TREND:{trend_bullish}")

# ---- 1m HANDLER (ENTRY + EXIT) ----
def on_1m(ws, msg):
    global ema_fast_1, ema_slow_1, dea_1
    global prev_dif_1, prev_dea_1
    global in_position, entry_price, trailing_sl

    if not trend_bullish:
        return  # 🚫 NO TREND → NO TRADE

    k = json.loads(msg)['k']
    if not k['x']:
        return

    close = float(k['c'])
    high = float(k['h'])
    low = float(k['l'])
    time = datetime.fromtimestamp(k['T'] / 1000)

    ema_fast_1 = ema(close, ema_fast_1, FAST)
    ema_slow_1 = ema(close, ema_slow_1, SLOW)

    dif = ema_fast_1 - ema_slow_1
    dea_1 = ema(dif, dea_1, SIGNAL)
    hist = dif - dea_1

    atr_val = update_atr(high, low, close)

    if prev_dif_1 is None or atr_val is None:
        prev_dif_1, prev_dea_1 = dif, dea_1
        return

    print(f"[1m ] {time} DIF:{dif:.8f} DEA:{dea_1:.8f} ATR:{atr_val:.8f}")

    # 🟢 ENTRY
    if (
        not in_position and
        prev_dif_1 < prev_dea_1 and
        dif > dea_1 and
        hist > 0
    ):
        in_position = True
        entry_price = close
        trailing_sl = close - atr_val * ATR_MULTIPLIER
        print(f"🟢 BUY @ {entry_price:.8f} SL:{trailing_sl:.8f}")

    # 🔁 TRAIL
    elif in_position:
        trailing_sl = max(trailing_sl, close - atr_val * ATR_MULTIPLIER)

        if close <= trailing_sl:
            print(f"❌ EXIT (ATR) @ {close:.8f}")
            in_position = False

        elif prev_dif_1 > prev_dea_1 and dif < dea_1:
            print(f"🔴 EXIT (MACD) @ {close:.8f}")
            in_position = False

    prev_dif_1, prev_dea_1 = dif, dea_1

# ---- START ----
def start():
    ws15 = websocket.WebSocketApp(SOCKET_15M, on_message=on_15m)
    ws1  = websocket.WebSocketApp(SOCKET_1M, on_message=on_1m)

    threading.Thread(target=ws15.run_forever, daemon=True).start()
    ws1.run_forever()

if __name__ == "__main__":
    start()
