"""
FEE-AWARE PnL TRACKER (BINANCE SPOT)
-----------------------------------
"""

class PnLTracker:

    @staticmethod
    def calculate_net_pnl(
        entry_price: float,
        exit_price: float,
        quantity: float,
        taker_fee: float
    ) -> dict:
        """
        Returns gross pnl, fees, net pnl
        """

        gross_pnl = (exit_price - entry_price) * quantity

        entry_fee = entry_price * quantity * taker_fee
        exit_fee = exit_price * quantity * taker_fee
        total_fees = entry_fee + exit_fee

        net_pnl = gross_pnl - total_fees

        return {
            "gross_pnl": round(gross_pnl, 4),
            "fees": round(total_fees, 4),
            "net_pnl": round(net_pnl, 4)
        }
