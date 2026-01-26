import os
import time
import pandas as pd
import ta

from binance.client import Client
from binance.streams import ThreadedWebsocketManager
from dotenv import load_dotenv
from utils.telegram import TelegramNotifier


class BinanceATRBot:
    def __init__(
        self,
        symbols,
        interval=Client.KLINE_INTERVAL_1MINUTE,
        initial_balance=10000.0,
        risk_per_trade=0.01,
        fee_pct=0.001,
        atr_period=14,
        atr_mult=1.0,
    ):
        # ===== ENV =====
        load_dotenv()
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")

        self.client = Client(self.api_key, self.api_secret)
        self.notifier = TelegramNotifier()

        # ===== CONFIG =====
        self.symbols = symbols
        self.interval = interval
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.fee_pct = fee_pct
        self.atr_period = atr_period
        self.atr_mult = atr_mult

        # ===== STATE =====
        self.state = {
            s: {
                "df": pd.DataFrame(),
                "balance": initial_balance,
                "qty": 0.0,
                "entry": 0.0,
                "sl": 0.0,
            }
            for s in symbols
        }

    # ================= INDICATORS =================
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) < self.atr_period + 5:
            return df

        df["rsi6"] = ta.momentum.RSIIndicator(df["close"], 6).rsi()

        macd = ta.trend.MACD(df["close"])
        df["dif"] = macd.macd()
        df["dea"] = macd.macd_signal()
        df["dif_prev"] = df["dif"].shift(1)
        df["dea_prev"] = df["dea"].shift(1)

        df["atr"] = ta.volatility.AverageTrueRange(
            df["high"],
            df["low"],
            df["close"],
            self.atr_period,
        ).average_true_range()

        return df

    # ================= TRADING =================
    def buy(self, symbol: str, price: float, atr: float):
        s = self.state[symbol]

        s["entry"] = price
        s["sl"] = price - atr * self.atr_mult

        risk_amt = s["balance"] * self.risk_per_trade
        qty = min(
            risk_amt / (price - s["sl"]),
            s["balance"] / price,
        )
        qty = round(qty, 0)

        if qty <= 0:
            return

        s["qty"] = qty
        s["balance"] -= qty * price * self.fee_pct

        self.notifier.send(
            f"🚀 <b>BUY</b>\n"
            f"Symbol: {symbol}\n"
            f"Price: {price:.8f}\n"
            f"SL: {s['sl']:.8f}\n"
            f"Qty: {qty}"
        )

        print(f"🟢 BUY {symbol} {qty} @ {price:.8f}")

    def sell(self, symbol: str, price: float):
        s = self.state[symbol]

        pnl = s["qty"] * (price - s["entry"])
        s["balance"] += pnl
        s["balance"] -= s["qty"] * price * self.fee_pct

        self.notifier.send(
            f"🔴 <b>SELL</b>\n"
            f"Symbol: {symbol}\n"
            f"Price: {price:.8f}\n"
            f"PnL: {pnl:.2f}\n"
            f"Balance: {s['balance']:.2f}"
        )

        print(f"🔴 SELL {symbol} @ {price:.8f} PnL={pnl:.2f}")

        s["qty"] = 0.0

    # ================= WS CALLBACK =================
    def on_kline(self, msg):
        if "k" not in msg:
            return

        k = msg["k"]
        print(k["s"], k["i"], "closed =", k["x"], "price =", k["c"])

        # only closed candles
        if not k["x"]:
            return

        symbol = k["s"]
        s = self.state[symbol]

        candle = {
            "time": pd.to_datetime(k["t"], unit="ms"),
            "open": float(k["o"]),
            "high": float(k["h"]),
            "low": float(k["l"]),
            "close": float(k["c"]),
            "volume": float(k["v"]),
        }

        s["df"] = pd.concat(
            [s["df"], pd.DataFrame([candle])],
            ignore_index=True,
        )

        s["df"] = self.add_indicators(s["df"])

        if len(s["df"]) < 50:
            return

        row = s["df"].iloc[-1]

        # ===== ENTRY =====
        if s["qty"] == 0:
            if (
                row["rsi6"] > 30
                and row["dif_prev"] < row["dea_prev"]
                and row["dif"] > row["dea"]
            ):
                self.buy(symbol, row["close"], row["atr"])

        # ===== EXIT =====
        else:
            if row["low"] <= s["sl"]:
                self.sell(symbol, s["sl"])
            elif (
                row["rsi6"] < 60
                and row["dif_prev"] > row["dea_prev"]
                and row["dif"] < row["dea"]
            ):
                self.sell(symbol, row["close"])

    # ================= START BOT =================
    def start(self):
        twm = ThreadedWebsocketManager(self.api_key, self.api_secret)
        twm.start()

        for sym in self.symbols:
            twm.start_kline_socket(
                callback=self.on_kline,
                symbol=sym,
                interval=self.interval,
            )

        print("🚀 Bot running 24×365 (Ctrl+C to stop)")
        while True:
            time.sleep(60)
