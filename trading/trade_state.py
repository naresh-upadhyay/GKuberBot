
class TradeState:
    def __init__(self, entry, stop, target, qty, atr):
        self.entry = entry
        self.initial_stop = stop
        self.stop = stop
        self.target = target
        self.qty = qty

        self.atr = atr
        self.risk = abs(entry - stop)
        self.breakeven_done = False

    def pnl(self, exit_price):
        return (exit_price - self.entry) * self.qty
