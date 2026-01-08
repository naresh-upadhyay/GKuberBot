
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

# Binance WebSocket URL (BTCUSDT trade stream)
SOCKET = "wss://stream.binance.com:9443/ws/pepeusdt@trade"


def on_open(ws):
    print("WebSocket connection opened")


def on_message(ws, message):
    data = json.loads(message)

    price = data['p']  # trade price
    quantity = data['q']  # trade quantity
    trade_time = data['T']
    print(f"Price: {price}, Qty: {quantity}, Time: {trade_time}")


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
