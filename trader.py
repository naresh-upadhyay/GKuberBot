import time
from trading.risk_manager import RiskManager
from risk.position_sizing import position_size_from_risk
from logger import logger
from trading.trailing_atr import ATRTrailingStopManager
from trading.trade_state import TradeState
from utils.telegram import TelegramNotifier
from utils.trade_journal import TradeJournal
"""
6️⃣ Best ATR Settings (Crypto Spot)
Market	ATR Multiplier
BTC / ETH	1.8 – 2.2
High volatility alts	2.2 – 2.8
Scalping (5m)	1.5
Swing (15m–1h)	2.5
🧠 Why ATR Trailing Is Superior
✅ Adapts to volatility
✅ Fewer fake stop-outs
✅ Bigger winners
✅ Same logic used in institutional systems
✅ Perfect for crypto
"""

class MultiSymbolTrader:

    def __init__(self, exchange, strategy, symbols, risk_pct):
        self.exchange = exchange
        self.strategy = strategy
        self.symbols = symbols
        self.risk_pct = risk_pct

        self.risk_manager = RiskManager(max_open_trades=2)
        self.trailing = ATRTrailingStopManager(atr_multiplier=2.0)
        self.notifier = TelegramNotifier()
        self.journal = TradeJournal()

    def open_trade(self, symbol, df):
        entry = df.iloc[-1]["close"]
        stop, target = self.strategy.trade_levels(entry)
        atr_value = df.iloc[-1]["atr"]

        qty = position_size_from_risk(
            self.exchange.get_balance("USDT"),
            self.risk_pct,
            entry,
            stop
        )

        if qty <= 0:
            return

        self.exchange.market_buy(symbol, qty)

        trade = TradeState(
            entry=entry,
            stop=stop,
            target=target,
            qty=qty,
            atr=atr_value
        )

        self.risk_manager.register_trade(symbol, trade)
        logger.info(f"🚀 BUY {symbol} @ {entry}")

        self.exchange.market_buy(symbol, qty)

        self.notifier.send(
            f"🚀 <b>BUY</b>\n"
            f"Symbol: {symbol}\n"
            f"Entry: {entry}\n"
            f"SL: {stop}\n"
            f"TP: {target}\n"
            f"Qty: {qty}"
        )


    def manage_trades(self, scanner):
        for symbol, trade in list(self.risk_manager.open_trades.items()):
            price = self.exchange.get_price(symbol)

            df = scanner.fetch_klines(symbol)
            df = self.strategy.prepare(df)
            current_atr = df.iloc[-1]["atr"]

            self.trailing.update(trade, price, current_atr)

            if price <= trade.stop:
                self.exchange.market_sell(symbol, trade.qty)
                self.risk_manager.close_trade(symbol)
                logger.warning(f"🛑 ATR STOP HIT {symbol}")
            elif price >= trade.target:
                self.exchange.market_sell(symbol, trade.qty)
                self.risk_manager.close_trade(symbol)
                logger.info(f"🎯 TARGET HIT {symbol}")


    def run(self, scanner):
        while True:
            print("hi king")
            signals = scanner.scan()

            for symbol in signals:
                if self.risk_manager.can_open_trade(symbol):
                    df = scanner.fetch_klines(symbol)
                    self.open_trade(symbol, df)

            self.manage_trades(scanner)
            time.sleep(30) #wait for 30 seconds

    def close_trade(self, symbol, trade, price, reason):
        self.exchange.market_sell(symbol, trade.qty)

        pnl = trade.pnl(price)
        self.journal.log(
            symbol, trade.entry, price, trade.qty, pnl, reason
        )

        self.notifier.send(
            f"📊 <b>EXIT</b>\n"
            f"Symbol: {symbol}\n"
            f"Exit: {price}\n"
            f"PnL: {round(pnl, 2)} USDT\n"
            f"Reason: {reason}"
        )

        self.risk_manager.close_trade(symbol)
