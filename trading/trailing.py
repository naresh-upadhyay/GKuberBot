from trading.trade_state import TradeState


class TrailingStopManager:

    def __init__(self, trail_pct=0.005):
        """
        trail_pct = 0.5% trailing stop
        """
        self.trail_pct = trail_pct

    def update(self, trade: TradeState, current_price: float):
        # 1️⃣ Breakeven logic
        if not trade.breakeven_done:
            if current_price >= trade.entry + trade.risk:
                trade.stop = trade.entry
                trade.breakeven_done = True
                print("✅ Stop moved to BREAKEVEN")

        # 2️⃣ Trailing stop logic
        if trade.breakeven_done:
            new_stop = current_price * (1 - self.trail_pct)
            if new_stop > trade.stop:
                trade.stop = new_stop
                print(f"🔁 Trailing stop updated → {round(trade.stop, 2)}")
