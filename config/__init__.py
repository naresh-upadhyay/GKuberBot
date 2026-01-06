from config.loader import load_env
from config.base import BaseConfig
from config.binance import BinanceConfig
from config.fees import FeeConfig
from config.risk import RiskConfig
from config.strategy import StrategyConfig
from config.telegram import TelegramConfig
from dotenv import load_dotenv

# load default env
load_dotenv()

# OR load specific env
load_dotenv(".env.prod", override=True)

class Config:
    def __init__(self):
        self.base = BaseConfig()
        self.binance = BinanceConfig()
        self.fees = FeeConfig()
        self.risk = RiskConfig()
        self.strategy = StrategyConfig()
        self.telegram = TelegramConfig()

config = Config()
