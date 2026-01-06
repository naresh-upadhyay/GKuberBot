"""
MULTI-SYMBOL RISK GOVERNOR
-------------------------
Controls:
- Total account risk
- Per-symbol exposure
- Daily loss & trade count
"""

from collections import defaultdict


class RiskGovernor:

    def __init__(
        self,
        max_total_risk: float,
        max_daily_loss: float,
        max_open_trades: int,
        max_trades_per_symbol: int,
        max_daily_trades: int
    ):
        self.max_total_risk = max_total_risk
        self.max_daily_loss = max_daily_loss
        self.max_open_trades = max_open_trades
        self.max_trades_per_symbol = max_trades_per_symbol
        self.max_daily_trades = max_daily_trades

        self.open_trades = {}               # trade_id → risk %
        self.symbol_trades = defaultdict(int)
        self.daily_loss = 0.0
        self.daily_trade_count = 0

    # ─────────────────────────────
    # CHECKS
    # ─────────────────────────────
    def can_open_trade(self, symbol: str, trade_risk: float) -> bool:
        if self.daily_loss >= self.max_daily_loss:
            print("❌ Daily loss limit reached")
            return False

        if self.daily_trade_count >= self.max_daily_trades:
            print("❌ Daily trade limit reached")
            return False

        if len(self.open_trades) >= self.max_open_trades:
            print("❌ Max open trades reached")
            return False

        if self.symbol_trades[symbol] >= self.max_trades_per_symbol:
            print(f"❌ Too many trades on {symbol}")
            return False

        total_risk = sum(self.open_trades.values()) + trade_risk
        if total_risk > self.max_total_risk:
            print("❌ Total account risk exceeded")
            return False

        return True

    # ─────────────────────────────
    # STATE UPDATES
    # ─────────────────────────────
    def register_trade(self, trade_id: str, symbol: str, risk: float):
        self.open_trades[trade_id] = risk
        self.symbol_trades[symbol] += 1
        self.daily_trade_count += 1

    def close_trade(self, trade_id: str, symbol: str, pnl: float):
        self.open_trades.pop(trade_id, None)
        self.symbol_trades[symbol] -= 1

        if pnl < 0:
            self.daily_loss += abs(pnl)

    def reset_daily_limits(self):
        self.daily_loss = 0.0
        self.daily_trade_count = 0
