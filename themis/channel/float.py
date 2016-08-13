import typing
import math

import themis.codegen
import themis.cgen

__all__ = ["FloatOutput", "FloatInput", "float_cell", "always_float"]


def _run_filter_op(a: float, op, b: float):
    if op == "+":
        return a + b
    elif op == "-":
        return a - b
    elif op == "*":
        return a * b
    elif op == "/":
        try:
            return a / b
        except ZeroDivisionError:
            assert b == 0
            return math.nan if a == 0 else math.copysign(math.inf, a)
    else:
        raise Exception("Unknown operator: %s" % op)


class FloatOutput:
    def __init__(self, instant: themis.cgen.Instant):
        assert isinstance(instant, themis.cgen.Instant)
        assert instant.is_param_type(float)
        self._instant = instant
        self._sets = {}

    def get_ref(self) -> themis.cgen.Instant:
        return self._instant

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def filter(self, filter_func, pre_args=(), post_args=()) -> "FloatOutput":
        instant = themis.cgen.Instant(float)
        instant.transform(filter_func, self.get_ref(), *pre_args, themis.cgen.Param, *post_args)
        return FloatOutput(instant)

    # note: different ramping scale than the CCRE
    # TODO: handle default targets better
    def add_ramping(self, change_per_second: float, update_rate_ms=None, default_target=0) -> "FloatOutput":
        import themis.timers
        update_rate_ms = update_rate_ms or 10
        ticker = themis.timers.ticker(update_rate_ms)
        max_delta = (change_per_second * (update_rate_ms / 1000.0))

        ramp_target = themis.cgen.Box(float(default_target))
        ramp_current = themis.cgen.Box(float(default_target))

        update_target = themis.cgen.Instant(float)
        update_target.set(ramp_target, themis.cgen.Param)

        update_ramping = themis.cgen.Instant(float)
        ticker.get_instant().transform("ramping_update", update_ramping, ramp_current, ramp_target, max_delta)
        update_ramping.set(ramp_current, themis.cgen.Param)
        update_ramping.invoke(self.get_ref(), themis.cgen.Param)

        return FloatOutput(update_target)

    def __add__(self, other: "FloatOutput") -> "FloatOutput":
        if not isinstance(other, FloatOutput):
            return NotImplemented

        instant = themis.cgen.Instant(float)
        instant.invoke(self.get_ref(), themis.cgen.Param)
        instant.invoke(other.get_ref(), themis.cgen.Param)

        return FloatOutput(instant)

    def __radd__(self, other: "FloatOutput") -> "FloatOutput":
        assert not isinstance(other, FloatOutput), "should not need to dispatch like that"
        return NotImplemented

    def __sub__(self, other: "FloatOutput") -> "FloatOutput":
        if isinstance(other, FloatOutput):
            return self + (-other)
        else:
            return NotImplemented

    def __rsub__(self, other: "FloatOutput") -> "FloatOutput":
        if isinstance(other, FloatOutput):
            return (-self) + other
        else:
            return NotImplemented

    def __neg__(self) -> "FloatOutput":
        instant = themis.cgen.Instant(float)
        instant.operator_transform("-", self.get_ref(), None, themis.cgen.Param)
        return FloatOutput(instant)

    def set_event(self, value: float) -> "themis.channel.event.EventOutput":
        assert isinstance(value, (int, float))
        value = float(value)
        if value not in self._sets:
            instant = themis.cgen.Instant(None)
            instant.invoke(self.get_ref(), value)
            self._sets[value] = themis.channel.EventOutput(instant)
        return self._sets[value]


class FloatInput:
    def __init__(self, instant: themis.cgen.Instant, default_value: float):
        assert isinstance(instant, themis.cgen.Instant)
        assert instant.is_param_type(float)
        assert isinstance(default_value, (int, float))
        self._instant = instant
        self._default_value = float(default_value)

    def send(self, output: FloatOutput) -> None:
        assert isinstance(output, FloatOutput)
        # TODO: default value?
        self._instant.invoke(output.get_ref(), themis.cgen.Param)

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def filter(self, filter_func, pre_args=(), post_args=()) -> "FloatInput":
        cell_out, cell_in = float_cell(0)  # TODO: default value
        self.send(cell_out.filter(filter_func=filter_func, pre_args=pre_args, post_args=post_args))
        return cell_in

    def operation(self, filter_op, other: "FloatInput") -> "FloatInput":
        cell_out, cell_in = float_cell(_run_filter_op(self._default_value, filter_op, other._default_value))

        value_self = themis.cgen.Box(self._default_value)
        value_other = themis.cgen.Box(other._default_value)

        for value, input in zip((value_self, value_other), (self, other)):
            input._instant.set(value, themis.cgen.Param)
            input._instant.operator_transform(filter_op, cell_out.get_ref(), value_self, value_other)
        return cell_in

    def deadzone(self, zone: float) -> "FloatInput":
        return self.filter("deadzone", (), (zone,))

    # note: different ramping scale than the CCRE
    def with_ramping(self, change_per_second: float, update_rate_ms=None) -> "FloatInput":
        cell_out, cell_in = float_cell(0)  # TODO: default value
        self.send(cell_out.add_ramping(change_per_second, update_rate_ms=update_rate_ms,
                                       default_target=0))
        return cell_in

    def _arith_op(self, op, other, reverse):
        if isinstance(other, (int, float)):
            other = float(other)
            if reverse:
                return self.filter(op, other)
            else:
                return self.filter(op, pre_args=(other,))
        elif isinstance(other, FloatInput):
            if reverse:
                return self.operation(op, other)
            else:
                return other.operation(op, self)
        else:
            return NotImplemented

    def __add__(self, other):
        return self._arith_op("+", other, False)

    def __radd__(self, other):
        return self._arith_op("+", other, True)

    def __sub__(self, other):
        return self._arith_op("-", other, False)

    def __rsub__(self, other):
        return self._arith_op("-", other, True)

    def __mul__(self, other):
        return self._arith_op("*", other, False)

    def __rmul__(self, other):
        return self._arith_op("*", other, True)

    def __truediv__(self, other):
        return self._arith_op("/", other, False)

    def __rtruediv__(self, other):
        return self._arith_op("/", other, True)

    def __neg__(self):
        cell_out, cell_in = float_cell(-self._default_value)
        self.send(-cell_out)
        return cell_in


def float_cell(default_value) -> typing.Tuple[FloatOutput, FloatInput]:
    instant = themis.cgen.Instant(float)
    return FloatOutput(instant), FloatInput(instant, default_value)


def always_float(value) -> FloatInput:
    return float_cell(value)[1]
