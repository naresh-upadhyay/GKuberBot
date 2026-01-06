import os

class StrategyConfig:
    def __init__(self):
        self.STRATEGY_NAME = os.getenv("STRATEGY_NAME", "ema_scalping")
        self.TIMEFRAME = os.getenv("TIMEFRAME", "1m")
        self.LEVERAGE = int(os.getenv("LEVERAGE", "1"))

    def as_dict(self):
        return {
            "strategy": self.STRATEGY_NAME,
            "timeframe": self.TIMEFRAME,
            "leverage": self.LEVERAGE
        }
