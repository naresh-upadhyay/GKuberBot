class RiskManager:

    def __init__(self, max_open_trades=2):
        self.max_open_trades = max_open_trades
        self.open_trades = {}

    def can_open_trade(self, symbol):
        return (
            symbol not in self.open_trades
            and len(self.open_trades) < self.max_open_trades
        )

    def register_trade(self, symbol, trade):
        self.open_trades[symbol] = trade

    def close_trade(self, symbol):
        if symbol in self.open_trades:
            del self.open_trades[symbol]
