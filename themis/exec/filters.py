

def deadzone(value, zone):
    return value if abs(value) >= zone else 0.0

def multiply(value, mul):
    return value * mul

def operator(cached_inputs, output, operator, arguments):
    output(operator(*cached_inputs, *arguments))
