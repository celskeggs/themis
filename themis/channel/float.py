import typing

import themis.pygen
import themis.codegen
import themis.exec

__all__ = ["FloatOutput", "FloatInput", "float_cell", "always_float"]


class FloatOutput:
    def __init__(self, instant: themis.pygen.Instant):
        assert isinstance(instant, themis.pygen.Instant)
        assert instant.is_param_type(float)
        self._instant = instant
        self._sets = {}

    def get_ref(self) -> themis.pygen.Instant:
        return self._instant

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def filter(self, filter_func, pre_args=(), post_args=()) -> "FloatOutput":
        instant = themis.pygen.Instant(float)
        instant.transform(filter_func, self.get_ref(), *pre_args, themis.pygen.Param, *post_args)
        return FloatOutput(instant)

    # note: different ramping scale than the CCRE
    # TODO: handle default targets better
    def add_ramping(self, change_per_second: float, update_rate_ms=None, default_target=0) -> "FloatOutput":
        import themis.timers
        update_rate_ms = update_rate_ms or 10
        ticker = themis.timers.ticker(update_rate_ms)
        max_change_per_update = (change_per_second * (update_rate_ms / 1000.0))

        ramp_target = themis.pygen.Box(float(default_target))
        ramp_current = themis.pygen.Box(float(default_target))

        update_target = themis.pygen.Instant(float)
        update_target.set(ramp_target, themis.pygen.Param)

        update_ramping = themis.pygen.Instant(float)
        ticker.get_instant().transform(themis.exec.filters.ramping_update, update_ramping, ramp_current, ramp_target,
                                       max_change_per_update)
        update_ramping.set(ramp_current, themis.pygen.Param)
        update_ramping.invoke(self.get_ref(), themis.pygen.Param)

        return FloatOutput(update_target)

    def __add__(self, other: "FloatOutput") -> "FloatOutput":
        if not isinstance(other, FloatOutput):
            return NotImplemented

        instant = themis.pygen.Instant(float)
        instant.invoke(self.get_ref(), themis.pygen.Param)
        instant.invoke(other.get_ref(), themis.pygen.Param)

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
        return self.filter(themis.exec.filters.negate)

    def set_event(self, value: float) -> "themis.channel.event.EventOutput":
        assert isinstance(value, (int, float))
        value = float(value)
        if value not in self._sets:
            instant = themis.pygen.Instant(None)
            instant.invoke(self.get_ref(), value)
            self._sets[value] = themis.channel.EventOutput(instant)
        return self._sets[value]


class FloatInput:
    def __init__(self, instant: themis.pygen.Instant, default_value: float):
        assert isinstance(instant, themis.pygen.Instant)
        assert instant.is_param_type(float)
        assert isinstance(default_value, (int, float))
        self._instant = instant
        self._default_value = float(default_value)

    def send(self, output: FloatOutput) -> None:
        assert isinstance(output, FloatOutput)
        # TODO: default value?
        self._instant.invoke(output.get_ref(), themis.pygen.Param)

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def filter(self, filter_func, pre_args=(), post_args=()) -> "FloatInput":
        cell_out, cell_in = float_cell(0)  # TODO: default value
        self.send(cell_out.filter(filter_func=filter_func, pre_args=pre_args, post_args=post_args))
        return cell_in

    def operation(self, filter_func, other: "FloatInput", *args, pre_args=()) -> "FloatInput":
        cell_out, cell_in = float_cell(filter_func(*pre_args, self._default_value, other._default_value, *args))

        value_self = themis.pygen.Box(self._default_value)
        value_other = themis.pygen.Box(other._default_value)

        for value, input in zip((value_self, value_other), (self, other)):
            input._instant.set(value, themis.pygen.Param)
            input._instant.transform(filter_func, cell_out.get_ref(), *pre_args, value_self, value_other, *args)
        return cell_in

    def deadzone(self, zone: float) -> "FloatInput":
        return self.filter(themis.exec.filters.deadzone, (), (zone,))

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
        return self._arith_op(themis.exec.filters.add, other, False)

    def __radd__(self, other):
        return self._arith_op(themis.exec.filters.add, other, True)

    def __sub__(self, other):
        return self._arith_op(themis.exec.filters.subtract, other, False)

    def __rsub__(self, other):
        return self._arith_op(themis.exec.filters.subtract, other, True)

    def __mul__(self, other):
        return self._arith_op(themis.exec.filters.multiply, other, False)

    def __rmul__(self, other):
        return self._arith_op(themis.exec.filters.multiply, other, True)

    def __truediv__(self, other):
        return self._arith_op(themis.exec.filters.divide, other, False)

    def __rtruediv__(self, other):
        return self._arith_op(themis.exec.filters.divide, other, True)

    def __neg__(self):
        return self.filter(themis.exec.filters.negate)


def float_cell(default_value) -> typing.Tuple[FloatOutput, FloatInput]:
    instant = themis.pygen.Instant(float)
    return FloatOutput(instant), FloatInput(instant, default_value)


def always_float(value) -> FloatInput:
    return float_cell(value)[1]
