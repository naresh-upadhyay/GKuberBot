from strategy.indicators import ema, rsi, atr
from backtest.position_sizing import calculate_position_size

class EMARsiStrategy:

    def __init__(
        self,
        ema_fast=9,
        ema_slow=21,
        rsi_period=14,
        rsi_min=50,
        rsi_max=70,
        risk_reward=2.0
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.rsi_min = rsi_min
        self.rsi_max = rsi_max
        self.risk_reward = risk_reward

    def prepare_indicators(self, df):
        df["ema_fast"] = ema(df["close"], self.ema_fast)
        df["ema_slow"] = ema(df["close"], self.ema_slow)
        df["rsi"] = rsi(df["close"], self.rsi_period)
        df["atr"] = atr(df, period=14)
        return df

    def check_entry(self, df, i):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        ema_cross_up = (
            prev["ema_fast"] < prev["ema_slow"]
            and curr["ema_fast"] > curr["ema_slow"]
        )

        rsi_ok = self.rsi_min < curr["rsi"] < self.rsi_max

        return ema_cross_up and rsi_ok

    def get_trade_levels(self, entry_price):
        stop_loss = entry_price * 0.99  # 1% SL
        take_profit = entry_price + (
            (entry_price - stop_loss) * self.risk_reward
        )
        return stop_loss, take_profit

    def position_size(self, balance, risk_pct, entry, stop):
        return calculate_position_size(
            balance=balance,
            risk_pct=risk_pct,
            entry_price=entry,
            stop_loss_price=stop
        )

    def should_buy(self, df):
        prev = df.iloc[-2]
        curr = df.iloc[-1]

        ema_cross = prev["ema_fast"] < prev["ema_slow"] and curr["ema_fast"] > curr["ema_slow"]
        rsi_ok = self.rsi_min < curr["rsi"] < self.rsi_max

        return ema_cross and rsi_ok
