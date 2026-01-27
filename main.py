from binance import Client

from exchange.binance_main_bot import BinanceATRBot

if __name__ == "__main__":
    bot = BinanceATRBot(
        symbols=["PEPEUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT"],
        interval=Client.KLINE_INTERVAL_4HOUR
    )
    bot.start()
