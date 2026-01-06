#!/usr/bin/env python3
"""
ENV GENERATOR FOR TRADING BOT
-----------------------------
Creates:
- .env.dev (development)
- .env.prod (production)

Includes:
- Binance config
- Trading fees
- Risk management
- Strategy settings
------------------------------

Generate both .env.dev and .env.prod
python envgen.py

Overwrite existing files
python envgen.py --overwrite

Generate only production env
python envgen.py --prod-only

Generate only development env
python envgen.py --dev-only

🛡️ Safety Defaults (IMPORTANT)
Setting	Value
Max open trades	2
Risk per trade	1%
Trailing stop	0.5%
Timeframe	5m
Market type	Spot

6️⃣ Best ATR Settings (Crypto Spot)
Market	ATR Multiplier
BTC / ETH	1.8 – 2.2
High volatility alts	2.2 – 2.8
Scalping (5m)	1.5
Swing (15m–1h)	2.5
"""

import os
import argparse
import secrets


ENV_DEV = ".env.dev"
ENV_PROD = ".env.prod"


DEV_CONFIG = {
    # ENV
    "ENVIRONMENT": "development",
    "LOG_LEVEL": "DEBUG",

    # BINANCE
    "BINANCE_API_KEY": "",
    "BINANCE_SECRET_KEY": "",
    "BINANCE_TESTNET": "True",

    # FEES
    "MAKER_FEE": "0.001",
    "TAKER_FEE": "0.001",

    # RISK MANAGEMENT
    "MAX_RISK_PER_TRADE": "0.01",
    "MAX_DAILY_LOSS": "0.03",
    "MAX_OPEN_TRADES": "3",

    # TRAILING STOP
    "TRAILING_ENABLED":"True",
    "TRAILING_PERCENT":"0.7", #Use 0.3%–0.7% trailing for crypto


    # MULTI-SYMBOL RISK CONTROL
    "MAX_TOTAL_RISK":"0.03",        # 3% total open risk
    "MAX_TRADES_PER_SYMBOL":"1",
    "MAX_DAILY_TRADES":"5",

    # STRATEGY
    "STRATEGY_NAME": "ema_scalping",
    "TIMEFRAME": "1m",
    "LEVERAGE": "5",

    # Symbols
    "SYMBOLS":"BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT",

    # Telegram
    "TELEGRAM_BOT_TOKEN": "8549760885:AAE7KaCpCw8ggHSel_lnP5TQ8uhPsLT44k8",
    "TELEGRAM_CHAT_ID": "7595294305",

}


PROD_CONFIG = {
    # ENV
    "ENVIRONMENT": "production",
    "LOG_LEVEL": "INFO",

    # BINANCE
    "BINANCE_API_KEY": "REPLACE_ME",
    "BINANCE_SECRET_KEY": "REPLACE_ME",
    "BINANCE_TESTNET": "False",

    # FEES (lower in production)
    "MAKER_FEE": "0.0002",
    "TAKER_FEE": "0.0004",

    # RISK MANAGEMENT (safer)
    "MAX_RISK_PER_TRADE": "0.005",
    "MAX_DAILY_LOSS": "0.02",
    "MAX_OPEN_TRADES": "2",

    # TRAILING STOP
    "TRAILING_ENABLED":"True",
    "TRAILING_PERCENT":"0.7", #Use 0.3%–0.7% trailing for crypto

    # STRATEGY
    "STRATEGY_NAME": "trend_following",
    "TIMEFRAME": "5m",
    "LEVERAGE": "3",

    # Symbols
    "SYMBOLS":"BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT",

    #Telegram
    "TELEGRAM_BOT_TOKEN":"8549760885:AAE7KaCpCw8ggHSel_lnP5TQ8uhPsLT44k8",
    "TELEGRAM_CHAT_ID":"7595294305",
}


def write_env_file(filename: str, data: dict, overwrite: bool):
    if os.path.exists(filename) and not overwrite:
        print(f"⚠️  {filename} already exists — skipping")
        return

    with open(filename, "w") as f:
        for key, value in data.items():
            f.write(f"{key}={value}\n")

    print(f"✅ Generated {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate .env files for trading bot"
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .env files"
    )

    parser.add_argument(
        "--prod-only",
        action="store_true",
        help="Generate only .env.prod"
    )

    parser.add_argument(
        "--dev-only",
        action="store_true",
        help="Generate only .env.dev"
    )

    args = parser.parse_args()

    if not args.prod_only:
        write_env_file(ENV_DEV, DEV_CONFIG, args.overwrite)

    if not args.dev_only:
        write_env_file(ENV_PROD, PROD_CONFIG, args.overwrite)


if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Trading Bot ENV Generator")
    print("=" * 50)
    main()
