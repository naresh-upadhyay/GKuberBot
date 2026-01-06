import os

class FeeConfig:
    def __init__(self):
        self.MAKER_FEE = float(os.getenv("MAKER_FEE", "0.001"))
        self.TAKER_FEE = float(os.getenv("TAKER_FEE", "0.001"))

    def calculate_fee(self, qty, price, is_maker=False):
        fee_rate = self.MAKER_FEE if is_maker else self.TAKER_FEE
        return qty * price * fee_rate
