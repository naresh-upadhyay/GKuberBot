from binance.streams import ThreadedWebsocketManager
import time

def handler(msg):
    print("RAW:", msg)

    if "k" in msg:
        k = msg["k"]
        print(
            "PARSED:",
            k["s"],
            k["i"],
            "x =", k["x"],
            "close =", k["c"]
        )

twm = ThreadedWebsocketManager()
twm.start()

twm.start_kline_socket(
    callback=handler,
    symbol="BTCUSDT",
    interval="1m"
)

print("Started test socket...")

while True:
    time.sleep(10)
