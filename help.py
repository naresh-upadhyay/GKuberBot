import json
import websocket
from datetime import datetime

# Binance Kline WebSocket URL
# Format: symbol@kline_interval
SOCKET = "wss://stream.binance.com:9443/ws/pepeusdt@kline_1m"


EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14

closes = []

ema_fast = None
ema_slow = None
prev_ema_fast = None
prev_ema_slow = None

avg_gain = None
avg_loss = None
prev_close = None

in_position = False

def calculate_ema(price, prev_ema, period):
    k = 2 / (period + 1)
    if prev_ema is None:
        return price
    return price * k + prev_ema * (1 - k)

def calculate_wilder_rsi(close):
    global avg_gain, avg_loss, prev_close

    if prev_close is None:
        prev_close = close
        return None

    change = close - prev_close
    gain = max(change, 0)
    loss = max(-change, 0)

    # First RSI calculation
    if avg_gain is None or avg_loss is None:
        closes.append(close)
        if len(closes) < RSI_PERIOD + 1:
            prev_close = close
            return None

        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))

        avg_gain = sum(gains[-RSI_PERIOD:]) / RSI_PERIOD
        avg_loss = sum(losses[-RSI_PERIOD:]) / RSI_PERIOD

    else:
        avg_gain = (avg_gain * (RSI_PERIOD - 1) + gain) / RSI_PERIOD
        avg_loss = (avg_loss * (RSI_PERIOD - 1) + loss) / RSI_PERIOD

    prev_close = close

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def on_open(ws):
    print("Connected to Binance WebSocket")

def on_message(ws, message):
    global ema_fast, ema_slow, prev_ema_fast, prev_ema_slow, in_position

    data = json.loads(message)
    kline = data['k']

    if kline['x']:  # candle closed
        close_price = float(kline['c'])
        close_time = datetime.fromtimestamp(kline['T'] / 1000)

        prev_ema_fast = ema_fast
        prev_ema_slow = ema_slow

        ema_fast = calculate_ema(close_price, ema_fast, EMA_FAST)
        ema_slow = calculate_ema(close_price, ema_slow, EMA_SLOW)

        rsi = calculate_wilder_rsi(close_price)

        print("RSI:", rsi)
        print("Close:", close_price)
        print("CloseTime:", close_time)
        print(closes)
        if not rsi or not prev_ema_fast or not prev_ema_slow:
            return

        print(
            f"[{close_time}] "
            f"Close: {close_price} | "
            f"EMA9 prev_ema_fast: {prev_ema_fast:.8f} | "
            f"EMA21 prev_ema_slow: {prev_ema_slow:.8f} | "
            f"EMA9 ema_fast: {ema_fast:.8f} | "
            f"EMA21 ema_slow: {ema_slow:.8f} | "
            f"RSI: {round(rsi,2)} |"
            f"InPos: {in_position}"
        )

        # ✅ Clean RSI + EMA strategy
        if (
            not in_position and
            prev_ema_fast < prev_ema_slow and
            ema_fast > ema_slow and
            40 < rsi < 70
        ):
            in_position = True
            print("🟢 STRONG BUY SIGNAL")

        elif (
            in_position and
            prev_ema_fast > prev_ema_slow and
            ema_fast < ema_slow and
            rsi < 60
        ):
            in_position = False
            print("🔴 STRONG SELL SIGNAL")


def on_error(ws, error):
    print("Error:", error)


def on_close(ws, close_status_code, close_msg):
    print("🔌 WebSocket closed")
    print("Status code:", close_status_code)
    print("Message:", close_msg)

if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        SOCKET,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    while True:
        try:
            ws.run_forever()
        except Exception as e:
            print("Reconnecting...", e)
