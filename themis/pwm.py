from collections import namedtuple

import themis.channel

# all in milliseconds
SpeedControlSpecs = namedtuple("SpeedControlSpecs", "rev_max rev_min rest fwd_min fwd_max frequency_hz")

# from WPILib HAL
TALON_SR = SpeedControlSpecs(0.989, 1.487, 1.513, 1.539, 2.037, 200.0)
JAGUAR = SpeedControlSpecs(0.697, 1.454, 1.507, 1.55, 2.31, 198.0)
VICTOR_OLD = SpeedControlSpecs(1.026, 1.49, 1.507, 1.525, 2.027, 100.0)
SERVO = SpeedControlSpecs(0.6, 1.6, 1.6, 1.6, 2.6, 50.0)  # essentially just linear from 0.6 to 2.6
VICTOR_SP = SpeedControlSpecs(0.997, 1.48, 1.50, 1.52, 2.004, 200.0)
SPARK = SpeedControlSpecs(0.999, 1.46, 1.50, 1.55, 2.003, 200.0)
SD540 = SpeedControlSpecs(0.94, 1.44, 1.50, 1.55, 2.05, 200.0)
TALON_SRX = SpeedControlSpecs(0.997, 1.48, 1.50, 1.52, 2.004, 200.0)


def filter_to(spec: SpeedControlSpecs, out: themis.channel.FloatOutput) -> themis.channel.FloatOutput:
    return out.filter("pwm_map", (), (spec.rev_max, spec.rev_min, spec.rest, spec.fwd_min, spec.fwd_max))
