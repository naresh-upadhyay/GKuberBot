import json
import csv
import os
from datetime import datetime, UTC
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from binance.client import Client
import ta


INTERVAL = Client.KLINE_INTERVAL_4HOUR

LOOKBACK_MONTHS = 51
RANK_LOOKBACK = 20

INITIAL_BALANCE = 10000.0
RISK_PER_TRADE = 0.01
FEE_PCT = 0.001

ATR_PERIOD = 14
ATR_MULT = 1.0
# =========================================

client = Client()

END_DATE = datetime.now(timezone.utc)
START_DATE = END_DATE - timedelta(days=LOOKBACK_MONTHS * 30)

# ================= CONFIG =================
OUTPUT_DIR = "data"
JSON_FILE = f"{OUTPUT_DIR}/binance_spot_symbols.json"
CSV_FILE  = f"{OUTPUT_DIR}/binance_spot_symbols.csv"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================= CLIENT =================
client = Client()

# ================= FETCH EXCHANGE INFO =================
exchange_info = client.get_exchange_info()

# ================= FETCH 24H TICKER (VOLUME) =================
# ✅ Correct method for python-binance
tickers = client.get_ticker()

# Convert ticker list → dict
ticker_map = {t["symbol"]: t for t in tickers}

spot_symbols = []


# ================= HELPERS =================
def decimals_from_step(step: float) -> int:
    step = f"{step:.10f}".rstrip("0")
    return len(step.split(".")[1]) if "." in step else 0

for s in exchange_info.get("symbols", []):

    if not s.get("isSpotTradingAllowed", False):
        continue
    if s.get("status") != "TRADING":
        continue

    symbol = s["symbol"]
    ticker = ticker_map.get(symbol, {})

    filters = {f["filterType"]: f for f in s.get("filters", [])}
    lot = filters.get("LOT_SIZE", {})
    price_filter = filters.get("PRICE_FILTER", {})
    min_notional = filters.get("NOTIONAL", {})

    step_size = float(lot.get("stepSize", 0))
    tick_size = float(price_filter.get("tickSize", 0))

    spot_symbols.append({
        "symbol": symbol,
        "baseAsset": s["baseAsset"],
        "quoteAsset": s["quoteAsset"],

        # ===== 24H MARKET DATA =====
        "lastPrice": float(ticker.get("lastPrice", 0)),
        "baseVolume_24h": float(ticker.get("volume", 0)),
        "quoteVolume_24h": float(ticker.get("quoteVolume", 0)),
        "tradeCount_24h": int(ticker.get("count", 0)),

        # ===== PRECISION =====
        "qtyPrecision": decimals_from_step(step_size),
        "pricePrecision": decimals_from_step(tick_size),

        # ===== FILTERS =====
        "minQty": float(lot.get("minQty", 0)),
        "stepSize": step_size,
        "minNotional": float(min_notional.get("minNotional", 0))
    })

# ================= VALIDATE =================
if not spot_symbols:
    print("❌ No SPOT symbols found")
    sys.exit(1)

# ================= SAVE JSON =================
with open(JSON_FILE, "w") as f:
    json.dump(
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "count": len(spot_symbols),
            "symbols": spot_symbols
        },
        f,
        indent=2
    )

# ================= SAVE CSV =================
with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=spot_symbols[0].keys())
    writer.writeheader()
    writer.writerows(spot_symbols)

# ================= DONE =================
print("✅ SUCCESS")
print(f"📊 SPOT symbols: {len(spot_symbols)}")
print(f"📄 JSON → {JSON_FILE}")
print(f"📄 CSV  → {CSV_FILE}")

# ================= FILTER & SORT SYMBOLS =================

usdt_symbols = sorted(
    [
        s for s in spot_symbols
    ],
    key=lambda x: x.get("quoteVolume_24h", 0),
    reverse=True
)

# Extract only symbol names if needed
symbol_list = [s["symbol"] for s in usdt_symbols]

"""

# ================= PREVIEW =================
print(f"✅ Filtered USDT symbols: {len(symbol_list)}")
print("Top 20 by volume:")
for s in usdt_symbols[:20]:
    print(
        s["symbol"],
        "| volume:", round(s["quoteVolume_24h"], 2),
        "| minNotional:", s["minNotional"]
    )

"""




# ================= DATA =================
def fetch_data(symbol):
    klines = client.get_historical_klines(
        symbol,
        INTERVAL,
        START_DATE.strftime("%d %b %Y"),
        END_DATE.strftime("%d %b %Y")
    )

    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "_","_","_","_","_","_"
    ])

    df = df[["time","open","high","low","close","volume"]]
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df[["open","high","low","close","volume"]] = df[
        ["open","high","low","close","volume"]
    ].astype(float)

    return df


def add_indicators(df):
    if df is None or len(df) < ATR_PERIOD:
        return None  # not enough data, skip symbol
    df["rsi6"] = ta.momentum.RSIIndicator(df["close"], 6).rsi()

    macd = ta.trend.MACD(df["close"])
    df["dif"] = macd.macd()
    df["dea"] = macd.macd_signal()
    df["dif_prev"] = df["dif"].shift(1)
    df["dea_prev"] = df["dea"].shift(1)

    df["atr"] = ta.volatility.AverageTrueRange(
        df["high"], df["low"], df["close"], ATR_PERIOD
    ).average_true_range()

    return df


# ================= STRATEGY =================
def backtest_single_coin(df):
    balance = INITIAL_BALANCE
    qty = entry = sl = 0.0
    trades = []
    equity = []

    for i in range(50, len(df)):
        row = df.iloc[i]

        if qty == 0:
            if (
                row["rsi6"] > 30
                and row["dif_prev"] < row["dea_prev"]
                and row["dif"] > row["dea"]
            ):
                entry = row["close"]
                sl = entry - row["atr"] * ATR_MULT

                risk_amt = balance * RISK_PER_TRADE
                qty = min(
                    risk_amt / (entry - sl),
                    balance / entry
                )

                balance -= qty * entry * FEE_PCT

        else:
            exit_price = None

            if row["low"] <= sl:
                exit_price = sl
            elif (
                row["rsi6"] < 60
                and row["dif_prev"] > row["dea_prev"]
                and row["dif"] < row["dea"]
            ):
                exit_price = row["close"]

            if exit_price:
                pnl = qty * (exit_price - entry)
                balance += pnl
                balance -= qty * exit_price * FEE_PCT
                trades.append(pnl)
                qty = 0

        equity.append(balance)

    return balance, trades, equity


# ================= ELIGIBILITY =================
eligible = {}
stats = {}
eligible_coins_list = []

print(f"\n===== ROLLING {LOOKBACK_MONTHS}-MONTH ELIGIBILITY =====")

for sym in symbol_list:
    df = add_indicators(fetch_data(sym))
    if df is None or len(df) < ATR_PERIOD:
        continue

    final_balance, trades, equity = backtest_single_coin(df)
    equity = np.array(equity)

    peak = np.maximum.accumulate(equity)
    if len(equity) < 2 or len(peak) < 2:
        print("⚠️ No valid trades / equity curve — skipping symbol")
        continue

    max_dd = ((equity - peak) / peak).min() * 100

    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]

    avg_win = np.mean(wins) if wins else 0
    avg_loss = abs(np.mean(losses)) if losses else 1
    wl = avg_win / avg_loss

    ret_pct = (final_balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100

    # ================= PROFIT REPORT =================
    profit = final_balance - INITIAL_BALANCE
    profit_pct = (profit / INITIAL_BALANCE) * 100

    print("\n===== PROFIT SUMMARY =====")
    print(f"{sym}")
    print(f"Initial Balance : {INITIAL_BALANCE:.2f} USDT")
    print(f"Final Balance   : {final_balance:.2f} USDT")

    if profit >= 0:
        print(f"Net Profit      : +{profit:.2f} USDT ({profit_pct:.2f}%)")
    else:
        print(f"Net Loss        : {profit:.2f} USDT ({profit_pct:.2f}%)")
    print(f"Return : {ret_pct:.2f}%")
    print(f"Trades : {len(trades)}")
    print(f"Max DD : {max_dd:.2f}%")
    print(f"W/L    : {wl:.2f}")
    print("==========================\n")

    #-----Save to csv start

    eligible_coins_list.append({
        "Symbol": sym,
        "Initial Balance" : f"{INITIAL_BALANCE:.2f} USDT",
        "Final Balance"   : f"{final_balance:.2f} USDT",
        "Net Profit"      : f"{profit:.2f} USDT ({profit_pct:.2f}%)",
        "Net Amount" : f"{final_balance:.2f}",
        "Return" : f"{ret_pct:.2f}%",
        "Trades" : f"{len(trades)}",
        "Max DD" : f"{max_dd:.2f}%",
        "W/L"    : f"{wl:.2f}",
        "Type": "✅ ELIGIBLE" if ret_pct >= 0 else "❌ DISABLED",
        "Lookback Months" : LOOKBACK_MONTHS
    })
    #-----Save to csv end

    if (
        #max_dd >= -15  and
        wl >= 1.8
        and ret_pct >= 0
    ):
        eligible[sym] = df
        stats[sym] = {
            "long_ret": ret_pct / 100,
            "wl_score": min(wl / 3.0, 1.0)
        }
        print("✅ ELIGIBLE")
    else:
        print("❌ DISABLED")

print("\nEligible Coins:", list(eligible.keys()))

# ================= SAVE CSV =================
CSV_FILE_ELIGIBLE  = f"{OUTPUT_DIR}/binance_eligible_spot_symbols.csv"
with open(CSV_FILE_ELIGIBLE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=eligible_coins_list[0].keys())
    writer.writeheader()
    writer.writerows(eligible_coins_list)

# ================= RANKING =================
def rank_coins_fixed(eligible_data, stats, lookback):
    scores = {}

    for sym, df in eligible_data.items():
        short_ret = (
            df["close"].iloc[-1] - df["close"].iloc[-lookback]
        ) / df["close"].iloc[-lookback]

        score = (
            0.5 * stats[sym]["long_ret"] +
            0.3 * short_ret +
            0.2 * stats[sym]["wl_score"]
        )

        scores[sym] = score

    return max(scores, key=scores.get)


top_coin = rank_coins_fixed(eligible, stats, RANK_LOOKBACK)

print("\n===== TOP RANKED COIN (FINAL) =====")
print(top_coin)
print("=================================\n")
