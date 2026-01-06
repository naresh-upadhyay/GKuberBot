class ATRTrailingStopManager:

    def __init__(self, atr_multiplier=2.0):
        self.atr_multiplier = atr_multiplier

    def update(self, trade, current_price, current_atr):
        # 1️⃣ Move to breakeven at +1R
        if not trade.breakeven_done:
            if current_price >= trade.entry + trade.risk:
                trade.stop = trade.entry
                trade.breakeven_done = True
                print("✅ Stop moved to BREAKEVEN")

        # 2️⃣ ATR trailing AFTER breakeven
        if trade.breakeven_done:
            new_stop = current_price - (current_atr * self.atr_multiplier)
            if new_stop > trade.stop:
                trade.stop = new_stop
                print(f"🔁 ATR Trailing Stop → {round(trade.stop, 2)}")
