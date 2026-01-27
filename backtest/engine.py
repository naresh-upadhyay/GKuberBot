import os
import pandas as pd
import ta
from binance.client import Client
from dotenv import load_dotenv

class MultiCoinBacktester:

    def __init__(self, symbols, interval, start_date, end_date,
                 initial_balance=10000.0, risk_per_trade=0.01,
                 fee_pct=0.001, atr_period=14, atr_mult=1.0):

        load_dotenv()
        self.client = Client(
            os.getenv("BINANCE_API_KEY"),
            os.getenv("BINANCE_API_SECRET"),
        )

        self.symbols = symbols
        self.interval = interval
        self.start_date = start_date
        self.end_date = end_date
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.fee_pct = fee_pct
        self.atr_period = atr_period
        self.atr_mult = atr_mult

        self.state = {
            s: {
                "balance": initial_balance,
                "qty": 0.0,
                "entry": 0.0,
                "sl": 0.0,
                "trades": [],
                "equity_curve": []
            }
            for s in symbols
        }

    def add_indicators(self, df):
        df["rsi6"] = ta.momentum.RSIIndicator(df["close"], 6).rsi()
        macd = ta.trend.MACD(df["close"])
        df["dif"] = macd.macd()
        df["dea"] = macd.macd_signal()
        df["dif_prev"] = df["dif"].shift(1)
        df["dea_prev"] = df["dea"].shift(1)
        df["atr"] = ta.volatility.AverageTrueRange(
            df["high"], df["low"], df["close"], self.atr_period
        ).average_true_range()
        return df.dropna()

    def fetch_klines(self, symbol):
        klines = self.client.get_historical_klines(
            symbol, self.interval, self.start_date, self.end_date
        )

        df = pd.DataFrame(
            klines,
            columns=["time","open","high","low","close","volume",
                     "_","_","_","_","_","_"]
        )

        df = df[["time","open","high","low","close","volume"]]
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df[["open","high","low","close","volume"]] = df[
            ["open","high","low","close","volume"]
        ].astype(float)

        return self.add_indicators(df)

    def buy(self, symbol, price, atr, time):
        s = self.state[symbol]
        sl = price - atr * self.atr_mult
        risk_amt = s["balance"] * self.risk_per_trade
        qty = min(risk_amt / (price - sl), s["balance"] / price)
        if qty <= 0:
            return

        s["qty"] = qty
        s["entry"] = price
        s["sl"] = sl
        s["balance"] -= qty * price * self.fee_pct
        s["trades"].append({"type":"BUY","time":time,"price":price,"qty":qty})

    def sell(self, symbol, price, time, reason):
        s = self.state[symbol]
        pnl = s["qty"] * (price - s["entry"])
        s["balance"] += pnl
        s["balance"] -= s["qty"] * price * self.fee_pct
        s["trades"].append({
            "type":"SELL","time":time,"price":price,"pnl":pnl,"reason":reason
        })
        s["qty"] = 0.0

    def run(self):
        for symbol in self.symbols:
            df = self.fetch_klines(symbol)
            s = self.state[symbol]

            for _, row in df.iterrows():
                equity = s["balance"] + s["qty"] * row["close"]
                s["equity_curve"].append({
                    "time": row["time"].isoformat(),
                    "equity": equity
                })

                if s["qty"] == 0:
                    if (
                        row["rsi6"] > 30 and
                        row["dif_prev"] < row["dea_prev"] and
                        row["dif"] > row["dea"]
                    ):
                        self.buy(symbol, row["close"], row["atr"], row["time"])
                else:
                    if row["low"] <= s["sl"]:
                        self.sell(symbol, s["sl"], row["time"], "SL")
                    elif (
                        row["rsi6"] < 60 and
                        row["dif_prev"] > row["dea_prev"] and
                        row["dif"] < row["dea"]
                    ):
                        self.sell(symbol, row["close"], row["time"], "SIGNAL")

        return self.summary()

    def summary(self):
        total_pnl = 0.0
        out = []

        for symbol, s in self.state.items():
            sells = [t for t in s["trades"] if t["type"] == "SELL"]
            wins = [t for t in sells if t["pnl"] > 0]
            pnl = s["balance"] - self.initial_balance
            total_pnl += pnl

            out.append({
                "symbol": symbol,
                "trades": len(sells),
                "wins": len(wins),
                "pnl": round(pnl, 2),
                "equity_curve": s["equity_curve"]
            })

        return {"symbols": out, "total_pnl": round(total_pnl, 2)}
