import os
from risk.risk_governor import RiskGovernor

class RiskConfig:
    def __init__(self):
        self.MAX_RISK_PER_TRADE = float(os.getenv("MAX_RISK_PER_TRADE", "0.01"))
        self.MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "0.03"))
        self.MAX_OPEN_TRADES = int(os.getenv("MAX_OPEN_TRADES", "3"))
        self.TRAILING_ENABLED = os.getenv("TRAILING_ENABLED", "false").lower() == "true"
        self.TRAILING_PERCENT = float(os.getenv("TRAILING_PERCENT", "0.01"))
        self.MAX_TOTAL_RISK = float(os.getenv("MAX_TOTAL_RISK", "0.03"))
        self.MAX_TRADES_PER_SYMBOL = int(os.getenv("MAX_TRADES_PER_SYMBOL", "1"))
        self.MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "5"))

        self.governor = RiskGovernor(
            max_total_risk=self.MAX_TOTAL_RISK,
            max_daily_loss=self.MAX_DAILY_LOSS,
            max_open_trades=self.MAX_OPEN_TRADES,
            max_trades_per_symbol=self.MAX_TRADES_PER_SYMBOL,
            max_daily_trades=self.MAX_DAILY_TRADES
        )


    def can_open_trade(self, current_trades):
        return current_trades < self.MAX_OPEN_TRADES

    def calculate_position_size(
        self,
        balance,
        entry_price,
        stop_loss_price,
        taker_fee
    ):
        risk_amount = balance * self.MAX_RISK_PER_TRADE
        price_risk = abs(entry_price - stop_loss_price)
        fee_risk = entry_price * taker_fee * 2

        return risk_amount / (price_risk + fee_risk)