import math

def adjust_quantity_to_step(qty, step_size, min_qty):
    """
    Adjust quantity to Binance LOT_SIZE rules
    """

    qty = math.floor(qty / step_size) * step_size

    if qty < min_qty:
        raise ValueError("Quantity below Binance minimum")

    return round(qty, 8)
