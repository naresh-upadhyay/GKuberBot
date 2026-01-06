import pandas as pd

class Scanner:

    def __init__(self, exchange, strategy, symbols):
        self.exchange = exchange
        self.strategy = strategy
        self.symbols = symbols

    def fetch_klines(self, symbol, interval="5m", limit=100):
        klines = self.exchange.client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )

        df = pd.DataFrame(klines, columns=[
            "time","open","high","low","close","volume",
            "_","_","_","_","_","_"
        ])

        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        return df

    def scan(self):
        signals = []

        for symbol in self.symbols:
            try:
                df = self.fetch_klines(symbol)
                df = self.strategy.prepare_indicators(df)

                if self.strategy.should_buy(df):
                    signals.append(symbol)

            except Exception as e:
                print(f"⚠️ {symbol} scan failed: {e}")

        return signals
