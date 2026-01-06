"""
BINANCE SPOT POSITION SIZER
---------------------------
Calculates safe quantity based on risk %
"""

class SpotPositionSizer:

    @staticmethod
    def calculate_quantity(
        balance: float,
        risk_percent: float,
        entry_price: float,
        stop_loss_price: float,
        taker_fee: float
    ) -> float:
        """
        Returns quantity to buy (SPOT)

        Example:
        balance = 1000 USDT
        risk_percent = 0.01 (1%)
        entry = 100
        stop = 98
        """

        if entry_price <= 0 or stop_loss_price <= 0:
            raise ValueError("Invalid price")

        risk_amount = balance * risk_percent

        price_risk = abs(entry_price - stop_loss_price)
        fee_risk = entry_price * taker_fee * 2  # buy + sell fee

        total_risk_per_unit = price_risk + fee_risk

        if total_risk_per_unit <= 0:
            raise ValueError("Invalid risk calculation")

        quantity = risk_amount / total_risk_per_unit
        return round(quantity, 6)
