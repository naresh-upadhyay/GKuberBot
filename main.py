from exchange.binance_main_bot import BinanceATRBot

if __name__ == "__main__":
    bot = BinanceATRBot(
        symbols=["PEPEUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT"]
    )
    bot.start()
