from binance.client import Client
from binance.enums import *

class BinanceSpot:

    def __init__(self, api_key, api_secret, fee_rate=0.001):
        self.client = Client(api_key, api_secret)
        self.fee_rate = fee_rate

    def get_balance(self, asset="USDT"):
        balance = self.client.get_asset_balance(asset)
        return float(balance["free"])

    def get_price(self, symbol):
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])

    def market_buy(self, symbol, qty):
        order = self.client.create_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )
        return order

    def market_sell(self, symbol, qty):
        order = self.client.create_order(
            symbol=symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )
        return order
