import math


def deadzone(value: float, zone: float) -> float:
    return value if abs(value) >= zone else 0.0


def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    try:
        return a / b
    except ZeroDivisionError:
        assert b == 0  # TODO: remove this assert after confirming behavior
        return math.nan if a == 0 else math.copysign(math.inf, a)


def negate(x: float) -> float:
    return -x


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
