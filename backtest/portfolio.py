class Portfolio:

    def __init__(self, balance: float):
        self.initial_balance = balance
        self.balance = balance
        self.open_positions = {}
        self.trade_log = []

    def open_trade(self, trade_id, symbol, entry_price, qty, fee):
        self.balance -= (entry_price * qty + fee)
        self.open_positions[trade_id] = {
            "symbol": symbol,
            "entry_price": entry_price,
            "qty": qty,
            "fees": fee
        }

    def close_trade(self, trade_id, exit_price, fee):
        trade = self.open_positions.pop(trade_id)
        gross = exit_price * trade["qty"]
        pnl = gross - (trade["entry_price"] * trade["qty"])
        pnl -= (trade["fees"] + fee)

        self.balance += gross - fee
        self.trade_log.append(pnl)
        return pnl
