def position_size_from_risk(
    balance: float,
    risk_pct: float,
    entry_price: float,
    stop_price: float
):
    """
    Example:
    balance = 1000 USDT
    risk_pct = 0.01 (1%)
    risk_amount = 10 USDT
    """
    risk_amount = balance * risk_pct
    stop_distance = abs(entry_price - stop_price)

    if stop_distance <= 0:
        return 0

    qty = risk_amount / stop_distance
    return round(qty, 6)
