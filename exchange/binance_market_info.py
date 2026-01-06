from binance.client import Client


class BinanceMarketInfo:
    def __init__(self, client: Client):
        self.client = client

    def get_lot_size(self, symbol: str):
        """
        Fetch LOT_SIZE filter from Binance
        Returns: step_size, min_qty
        """

        exchange_info = self.client.get_symbol_info(symbol)
        if not exchange_info:
            raise ValueError(f"Symbol {symbol} not found")

        for f in exchange_info["filters"]:
            if f["filterType"] == "LOT_SIZE":
                step_size = float(f["stepSize"])
                min_qty = float(f["minQty"])
                return step_size, min_qty

        raise ValueError("LOT_SIZE filter not found")
