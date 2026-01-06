from config import config
from risk.spot_position_sizer import SpotPositionSizer
from exchange.binance_spot_executor import BinanceSpotExecutor
from exchange.binance_utils import adjust_quantity_to_step

from risk.pnl_tracker import PnLTracker

from risk.trailing_stop import TrailingStopManager

print(config.binance.as_dict())
print(config.strategy.as_dict())

fee = config.fees.calculate_fee(qty=0.01, price=50000)
print("Trading fee:", fee)

if config.risk.can_open_trade(current_trades=1):
    print("Trade allowed")

balance = 1000
entry_price = 50000
stop_loss_price = 49500

position_size = config.risk.calculate_position_size(
    balance=balance,
    entry_price=entry_price,
    stop_loss_price=stop_loss_price,
    taker_fee=config.fees.TAKER_FEE
)

print("Position size:", position_size)

SYMBOL = "BTCUSDT"

balance = 1000           # USDT balance
entry_price = 50000
stop_loss_price = 49500

# 1️⃣ Calculate quantity
qty = SpotPositionSizer.calculate_quantity(
    balance=balance,
    risk_percent=config.risk.MAX_RISK_PER_TRADE,
    entry_price=entry_price,
    stop_loss_price=stop_loss_price,
    taker_fee=config.fees.TAKER_FEE
)

# Example exchange rules (normally fetched from Binance API)
STEP_SIZE = 0.00001
MIN_QTY = 0.0001

qty = adjust_quantity_to_step(qty, STEP_SIZE, MIN_QTY)

print("Final quantity:", qty)

# 2️⃣ Execute trade
executor = BinanceSpotExecutor(
    api_key=config.binance.API_KEY,
    secret_key=config.binance.SECRET_KEY,
    testnet=config.binance.TESTNET
)

executor.place_market_buy(SYMBOL, qty)
executor.place_stop_loss(SYMBOL, qty, stop_loss_price)

market_info = BinanceMarketInfo(executor.client)
step_size, min_qty = market_info.get_lot_size("BTCUSDT")

qty = adjust_quantity_to_step(qty, step_size, min_qty)


result = PnLTracker.calculate_net_pnl(
    entry_price=50000,
    exit_price=50500,
    quantity=0.01,
    taker_fee=config.fees.TAKER_FEE
)

print(result)


trailing = TrailingStopManager(
    entry_price=50000,
    initial_stop=49500,
    trailing_percent=0.01
)

prices = [50100, 50300, 50500, 50400, 50200]

for price in prices:
    stop = trailing.update_price(price)
    print(f"Price: {price}, Stop: {stop}")

    if trailing.should_exit(price):
        print("🚨 Stop hit → Exit trade")
        break

while True:
    current_price = get_latest_price()  # WebSocket or REST

    trailing_stop = trailing.update_price(current_price)

    if trailing.should_exit(current_price):
        executor.market_sell(SYMBOL, qty)
        print("Trade exited via trailing stop")
        break

trade_id = "BTCUSDT_001"
symbol = "BTCUSDT"
risk = config.risk.MAX_RISK_PER_TRADE

# BEFORE trade
if not config.risk.governor.can_open_trade(symbol, risk):
    print("Trade blocked")
    return

# REGISTER trade
config.risk.governor.register_trade(trade_id, symbol, risk)

# EXECUTE trade...
pnl = -12.5  # example loss

# CLOSE trade
config.risk.governor.close_trade(trade_id, symbol, pnl)

#Call this once per day (cron / scheduler):
config.risk.governor.reset_daily_limits()
