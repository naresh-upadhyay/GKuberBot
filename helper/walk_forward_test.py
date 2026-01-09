import numpy as np

from backtest_portfolio_final_pro import (
    portfolio_backtest,
    market,
)

# ================= CONFIG =================
TRAIN_START = "1 Jan 2023"
TRAIN_END   = "1 Jan 2024"

TEST_START  = "1 Jan 2024"
TEST_END    = "1 Jan 2025"
# ==========================================


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


# ================= TRAIN =================
train_data = slice_market_data(market, TRAIN_START, TRAIN_END)
train_balance, train_trades, train_equity = portfolio_backtest(train_data)

train_dd = max_drawdown(train_equity)

# ================= TEST =================
test_data = slice_market_data(market, TEST_START, TEST_END)
test_balance, test_trades, test_equity = portfolio_backtest(test_data)

test_dd = max_drawdown(test_equity)

# ================= RESULT =================
print("\n====== WALK-FORWARD RESULT ======")
print(f"TRAIN Period     : {TRAIN_START} → {TRAIN_END}")
print(f"TRAIN Balance    : {train_balance:.2f}")
print(f"TRAIN Trades     : {len(train_trades)}")
print(f"TRAIN Max DD     : {train_dd:.2f}%")
print("--------------------------------")
print(f"TEST Period      : {TEST_START} → {TEST_END}")
print(f"TEST Balance     : {test_balance:.2f}")
print(f"TEST Trades      : {len(test_trades)}")
print(f"TEST Max DD      : {test_dd:.2f}%")
print("================================\n")
