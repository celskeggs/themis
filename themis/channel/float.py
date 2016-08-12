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

        ramp_target = themis.codegen.add_variable(default_target)
        ramp_current = themis.codegen.add_variable(default_target)

        @float_build
        def update_target(ref: str):
            yield "global %s" % ramp_target
            yield "%s = value" % ramp_target

        @themis.channel.event.event_build
        def update_ramping(ref: str):
            yield "global %s, %s" % (ramp_target, ramp_current)
            yield "%s = %s(%s, %s, %s)" % (
                ramp_current, themis.codegen.ref(themis.exec.filters.ramping_update), ramp_current, ramp_target,
                max_change_per_update)
            yield "%s(%s)" % (self.get_float_ref(), ramp_current)

        ticker.send(update_ramping)
        return update_target

    def __add__(self, other: "FloatOutput") -> "FloatOutput":
        if not isinstance(other, FloatOutput):
            return NotImplemented

        @float_build
        def combined(ref: str):
            yield "%s(value)" % self.get_float_ref()
            yield "%s(value)" % other.get_float_ref()

        return combined

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
        cell_out, cell_in = float_cell(0)  # TODO: default value

        filter_ref = themis.codegen.ref(filter_func)
        args = themis.codegen.ref(args)
        pre_args = themis.codegen.ref(pre_args)

        value_self = themis.codegen.add_variable(0)  # TODO: default value
        value_other = themis.codegen.add_variable(0)
        for value, input in zip((value_self, value_other), (self, other)):
            @float_build
            def update(ref: str):
                yield "global %s, %s" % (value_self, value_other)
                yield "%s = value" % (value,)
                yield "%s(%s(*%s, %s, %s, *%s))" % \
                      (cell_out.get_float_ref(), filter_ref, pre_args, value_self, value_other, args)

            input.send(update)
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
