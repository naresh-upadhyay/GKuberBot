def calculate_position_size(
    balance: float,
    risk_pct: float,
    entry_price: float,
    stop_loss_price: float
):
    risk_amount = balance * risk_pct
    stop_distance = abs(entry_price - stop_loss_price)

    qty = risk_amount / stop_distance
    return round(qty, 6)
