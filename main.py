from exchange.binance_spot import BinanceSpot
from strategy.ema_rsi import EMARsiStrategy
from scanner import Scanner
from trader import MultiSymbolTrader
import os

if __name__ == "__main__":

    symbols = [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT"
    ]

    exchange = BinanceSpot(
        api_key=os.getenv("BINANCE_API_KEY"),
        api_secret=os.getenv("BINANCE_API_SECRET")
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
