import numpy as np
import pandas as pd

import backtest_portfolio_final_pro as cfg
from backtest_portfolio_final_pro import portfolio_backtest, market


# ================= TRAIN PERIOD =================
TRAIN_START = "1 Jan 2023"
TRAIN_END   = "1 Jan 2026"
# ================================================


def slice_market_data(data, start, end):
    sliced = {}
    for symbol, df in data.items():
        mask = (df["time"] >= start) & (df["time"] < end)
        sliced[symbol] = df.loc[mask].reset_index(drop=True)
    return sliced


def max_drawdown(equity_curve):
    if len(equity_curve) == 0:
        return 0.0
    equity = np.array(equity_curve)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return dd.min() * 100


# ================= TRAIN DATA =================
train_data = slice_market_data(market, TRAIN_START, TRAIN_END)


# ================= DISCOVERY GRID =================
ATR_MULTS = [2.0, 2.5, 3.0]
ADX_LEVELS = [15, 20]
MAX_TRADES = [2, 3]
# ================================================


results = []

# 🔓 DISCOVERY MODE FLAGS (TRAIN ONLY)
cfg.USE_BTC_REGIME_FILTER = False
cfg.USE_RSI_FILTER = False

for atr in ATR_MULTS:
    for adx in ADX_LEVELS:
        for max_pos in MAX_TRADES:

            cfg.ATR_MULT = atr
            cfg.ADX_MIN = adx
            cfg.MAX_OPEN_TRADES = max_pos

            final_balance, trades, equity = portfolio_backtest(train_data)
            dd = max_drawdown(equity)

            results.append({
                "ATR_MULT": atr,
                "ADX_MIN": adx,
                "MAX_TRADES": max_pos,
                "FINAL_BALANCE": round(final_balance, 2),
                "TRADES": len(trades),
                "MAX_DD_%": round(dd, 2)
            })


df = pd.DataFrame(results)

filtered = df[
    (df["TRADES"] >= 20) &
    (df["TRADES"] <= 300) &
    (df["MAX_DD_%"] >= -30)
].sort_values(by=["FINAL_BALANCE", "TRADES"], ascending=False)

print("\n====== TRAIN-ONLY DISCOVERY (RSI OFF, BTC OFF) ======")
print(filtered.head(10))
print("====================================================\n")

filtered.to_csv("train_discovery_candidates.csv", index=False)

# 🔒 RE-ENABLE FINAL LOGIC
cfg.USE_BTC_REGIME_FILTER = True
cfg.USE_RSI_FILTER = True
