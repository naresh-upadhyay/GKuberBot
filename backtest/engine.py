class BacktestEngine:

    def __init__(
        self,
        df,
        broker,
        portfolio,
        risk_governor,
        strategy,
        risk_per_trade
    ):
        self.df = strategy.prepare_indicators(df)
        self.broker = broker
        self.portfolio = portfolio
        self.risk_governor = risk_governor
        self.strategy = strategy
        self.risk_per_trade = risk_per_trade

    def run(self):
        for i in range(50, len(self.df) - 1):
            price = self.df.iloc[i]["close"]
            symbol = "BTCUSDT"

            if self.strategy.check_entry(self.df, i):
                if not self.risk_governor.can_open_trade(symbol, self.risk_per_trade):
                    continue

                stop, target = self.strategy.get_trade_levels(price)
                qty = self.strategy.position_size(
                    self.portfolio.balance,
                    self.risk_per_trade,
                    price,
                    stop
                )

                buy = self.broker.execute_buy(price, qty)
                trade_id = f"{symbol}_{i}"

                self.portfolio.open_trade(
                    trade_id, symbol, price, qty, buy["fee"]
                )

                # simulate forward candles
                for j in range(i + 1, len(self.df)):
                    candle = self.df.iloc[j]

                    if candle["low"] <= stop:
                        sell_price = stop
                        break
                    elif candle["high"] >= target:
                        sell_price = target
                        break
                else:
                    sell_price = self.df.iloc[-1]["close"]

                sell = self.broker.execute_sell(sell_price, qty)
                pnl = self.portfolio.close_trade(trade_id, sell_price, sell["fee"])

                self.risk_governor.close_trade(trade_id, symbol, pnl)
