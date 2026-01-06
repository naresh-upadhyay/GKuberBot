"""
BINANCE SPOT TRAILING STOP
--------------------------
Server-side trailing stop logic
"""

class TrailingStopManager:

    def __init__(
        self,
        entry_price: float,
        initial_stop: float,
        trailing_percent: float
    ):
        self.entry_price = entry_price
        self.initial_stop = initial_stop
        self.trailing_percent = trailing_percent

        self.highest_price = entry_price
        self.current_stop = initial_stop

    def update_price(self, current_price: float) -> float:
        """
        Call this on every price update.
        Returns updated stop-loss price.
        """

        # Update highest price
        if current_price > self.highest_price:
            self.highest_price = current_price

            # Calculate new trailing stop
            new_stop = self.highest_price * (1 - self.trailing_percent)

            # Move stop only UP (never down)
            if new_stop > self.current_stop:
                self.current_stop = round(new_stop, 2)

        return self.current_stop

    def should_exit(self, current_price: float) -> bool:
        """
        Check if stop-loss hit
        """
        return current_price <= self.current_stop
