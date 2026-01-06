class SimulatedBroker:

    def __init__(self, fee_rate: float):
        self.fee_rate = fee_rate

    def execute_buy(self, price, qty):
        fee = price * qty * self.fee_rate
        return {
            "price": price,
            "qty": qty,
            "fee": fee
        }

    def execute_sell(self, price, qty):
        fee = price * qty * self.fee_rate
        return {
            "price": price,
            "qty": qty,
            "fee": fee
        }
