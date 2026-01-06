from binance.client import Client
from exchange.binance_utils import adjust_quantity_to_step


class BinanceSpotExecutor:

    def __init__(self, api_key, secret_key, testnet=True):
        self.client = Client(api_key, secret_key)
        if testnet:
            self.client.API_URL = "https://testnet.binance.vision/api"

    def place_market_buy(self, symbol, quantity):
        return self.client.order_market_buy(
            symbol=symbol,
            quantity=quantity
        )

    def place_stop_loss(self, symbol, quantity, stop_price):
        return self.client.create_order(
            symbol=symbol,
            side="SELL",
            type="STOP_LOSS_LIMIT",
            timeInForce="GTC",
            quantity=quantity,
            stopPrice=round(stop_price, 2),
            price=round(stop_price * 0.999, 2)
        )

    def market_sell(self, symbol, quantity):
        return self.client.order_market_sell(
            symbol=symbol,
            quantity=quantity
        )
