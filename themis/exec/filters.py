import math


def deadzone(value, zone):
    return value if abs(value) >= zone else 0.0


def multiply(value, mul):
    return value * mul


def operator(cached_inputs, output, operator, arguments):
    output(operator(*cached_inputs, *arguments))


def pwm_map(value: float, rev_max: float, rev_min: float, center: float, fwd_min: float, fwd_max: float) -> float:
    if value < 0:
        value = min(1, -value)
        return value * (rev_max - rev_min) + rev_min
    elif value > 0:
        value = min(1, value)
        return value * (fwd_max - fwd_min) + fwd_min
    elif math.isnan(value):
        return value
    else:
        return center
