import os

class BinanceConfig:
    def __init__(self):
        self.API_KEY = os.getenv("BINANCE_API_KEY", "")
        self.SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
        self.TESTNET = os.getenv("BINANCE_TESTNET", "True") == "True"

    def as_dict(self):
        return {
            "api_key": self.API_KEY,
            "secret_key": self.SECRET_KEY,
            "testnet": self.TESTNET
        }
