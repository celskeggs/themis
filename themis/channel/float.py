import typing

import themis.codegen
import themis.exec

__all__ = ["FloatOutput", "FloatInput", "float_cell", "always_float"]


class FloatOutput:
    def __init__(self, reference: str):
        assert isinstance(reference, str)
        self._ref = reference

    def get_float_ref(self) -> str:
        return self._ref

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def filter(self, filter_func, *args, pre_args=()) -> "FloatOutput":
        filter_ref = themis.codegen.ref(filter_func)
        pre_args = themis.codegen.ref(pre_args)
        args = themis.codegen.ref(args)

        @float_build
        def update(ref: str):
            yield "%s(%s(*%s, value, %s))" % (self.get_float_ref(), filter_ref, pre_args, args)

        return update

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
            yield "globals %s" % ramp_target
            yield "%s = value" % ramp_target

        @themis.channel.event.event_build
        def update_ramping(ref: str):
            yield "globals %s, %s" % (ramp_target, ramp_current)
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


class FloatInput:
    def __init__(self, targets: list):
        assert isinstance(targets, list)
        self._targets = targets

    def send(self, output: FloatOutput) -> None:
        assert isinstance(output, FloatOutput)
        # TODO: default value?
        self._targets.append(output.get_float_ref())

    def filter(self, filter_ref, *args, pre_args=()) -> "FloatInput":
        cell_out, cell_in = float_cell()  # TODO: default value
        self.send(cell_out.filter(filter_ref=filter_ref, *args, pre_args=pre_args))
        return cell_in

    def operation(self, filter_ref, other: "FloatInput", *args, pre_args=()) -> "FloatInput":
        import themis.codehelpers  # here to avoid issues with circular references
        cell = FloatCell()
        ref = "ref%d" % themis.codegen.next_uid()
        for ab, inp in zip("ab", (self, other)):
            themis.codegen.add_code("v%s_%s = %s" % (ab, ref, inp.default_value()))
            themis.codegen.add_code(
                "def m%s_%s(fv):\n\tglobals va_%s, vb_%s\n\tv%s_%s = fv\n\t%s(%s(*%s, va_%s, vb_%s, *%s))"
                % (ab, ref, ref, ref, ab, ref, cell.get_reference(), themis.codegen.ref(filter_ref),
                   themis.codegen.ref(pre_args), ref, ref, themis.codegen.ref(args)))
            inp.send(themis.codehelpers.FloatWrapper("m%s_%s" % (ab, ref)))
        cell.send_default_value(filter_ref(*pre_args, self.default_value(), other.default_value(), *args))
        return cell

    def deadzone(self, zone: float) -> "FloatInput":
        return self.filter(themis.exec.filters.deadzone, zone)

    # note: different ramping scale than the CCRE
    def with_ramping(self, change_per_second: float, update_rate_ms=None) -> "FloatInput":
        cell_out, cell_in = float_cell()
        self.send(cell_out.add_ramping(change_per_second, update_rate_ms=update_rate_ms,
                                       default_target=self.default_value()))
        return cell_in

    def _arith_op(self, op, other, reverse):
        if isinstance(other, (int, float)):
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


def float_build(body_gen) -> FloatOutput:
    def gen(ref: str):
        yield "def %s(value) -> None:" % ref
        for line in body_gen(ref):
            yield "\t%s" % (line,)

    return FloatOutput(themis.codegen.add_code_gen_ref(gen))


def float_cell(default_value) -> typing.Tuple[FloatOutput, FloatInput]:
    # TODO: use default_value
    targets = []

    @float_build
    def dispatch(ref: str):
        if targets:
            for target in targets:
                yield "%s(value)" % (target,)
        else:
            yield "pass"

    return dispatch, FloatInput(targets)


def always_float(value):
    return float_cell(value)[1]
