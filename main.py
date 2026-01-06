from config import config
from exchange.binance_spot import BinanceSpot
from strategy.ema_rsi import EMARsiStrategy
from scanner import Scanner
from trader import MultiSymbolTrader

if __name__ == "__main__":

    symbols = [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT"
    ]

    exchange = BinanceSpot(
        api_key=config.binance.API_KEY,
        api_secret=config.binance.SECRET_KEY
    )

    strategy = EMARsiStrategy()

    scanner = Scanner(exchange, strategy, symbols)

    trader = MultiSymbolTrader(
        exchange=exchange,
        strategy=strategy,
        symbols=symbols,
        risk_pct=0.01
    )

    trader.run(scanner)
