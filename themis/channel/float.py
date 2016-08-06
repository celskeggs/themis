import abc
import typing

import themis.codegen
import themis.exec

__all__ = ["FloatOutput", "FloatInput", "FloatCell", "always_float"]


class FloatOutput(abc.ABC):
    @abc.abstractmethod
    def get_reference(self) -> str:
        pass

    @abc.abstractmethod
    def send_default_value(self, value: float):  # TODO: add assertions to targets to ensure output isolation
        pass

    def filter(self, filter_ref, *args, pre_args=()) -> "FloatOutput":
        return FilterFloatOutput(self, filter_ref, pre_args, args)

    # note: different ramping scale than the CCRE
    # TODO: handle default targets better
    def add_ramping(self, change_per_second: float, update_rate_ms=None,
                    default_target=0) -> "FloatOutput":
        import themis.timers
        import themis.codehelpers
        if update_rate_ms is None:
            update_rate_ms = 10
        ticker = themis.timers.ticker(update_rate_ms)
        max_change_per_update = (change_per_second * (update_rate_ms / 1000.0))
        ref = "ramp%d" % themis.codegen.next_uid()
        themis.codegen.add_code("target_%s = %s" % (ref, default_target))
        themis.codegen.add_code("out_%s = %s" % (ref, default_target))
        themis.codegen.add_code("def f_%s(fv):\n\ttarget_%s = fv" % (ref, ref))
        themis.codegen.add_code("def e_%s(fv):\n\tout_%s = %s(out_%s, target_%s, %s)\n\t%s(out_%s)" % (
            ref, ref, themis.codegen.ref(themis.exec.filters.ramping_update), ref, ref, max_change_per_update,
            self.get_reference(), ref))
        self.send_default_value(default_target)
        ticker.send(themis.codehelpers.EventWrapper("e_%s" % ref))
        return themis.codehelpers.FloatWrapper("f_%s" % ref)

    def __add__(self, other):
        if isinstance(other, FloatOutput):
            return CombinedFloatOutput(self, other)
        else:
            return NotImplemented

    def __radd__(self, other):
        if isinstance(other, FloatOutput):
            return CombinedFloatOutput(other, self)
        else:
            return NotImplemented

    def __sub__(self, other):
        if isinstance(other, FloatOutput):
            return CombinedFloatOutput(self, -other)
        else:
            return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, FloatOutput):
            return CombinedFloatOutput(-self, other)
        else:
            return NotImplemented

    def __neg__(self):
        return self.filter(themis.exec.filters.negate)


# TODO: make FloatCells cast to FloatInputs not be accessible as FloatOutputs.
class FloatInput(abc.ABC):
    @abc.abstractmethod
    def send(self, output: FloatOutput) -> None:
        output.send_default_value(self.default_value())

    @abc.abstractmethod
    def default_value(self) -> float:
        pass

    def filter(self, filter_ref, *args, pre_args=()) -> "FloatInput":
        return FilterFloatInput(self, filter_ref, pre_args, args)

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
        cell = FloatCell()
        self.send(cell.add_ramping(change_per_second, update_rate_ms=update_rate_ms,
                                   default_target=self.default_value()))
        return cell

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


class FloatCell(themis.codegen.RefGenerator, FloatInput, FloatOutput):
    def __init__(self, value=0.0):  # TODO: perhaps we should initialize to NaN instead?
        super().__init__()
        self._default_value = value
        self._default_value_queried = False
        self._targets = []
        themis.codegen.add_import("math")  # for math.isnan in generate_ref_code

    def default_value(self):
        self._default_value_queried = True
        return self._default_value

    def send(self, target: FloatOutput):
        super(FloatCell, self).send(target)
        self._targets.append(target)

    def send_default_value(self, value: float):
        if value != self._default_value:
            assert not self._default_value_queried, "Default value changed after usage!"

    def generate_ref_code(self, ref):
        yield "value_%s = %s" % (ref, self._default_value)
        yield "def %s(fv: float) -> None:" % ref
        yield "\tglobals value_%s" % ref
        yield "\tif fv == value_%s or (math.isnan(fv) and math.isnan(value_%s)): return" % (ref, ref)
        yield "\tvalue_%s = fv" % ref
        for target in self._targets:
            yield "\t%s(fv)" % target.get_reference()


class FilterFloatInput(FloatInput):
    def __init__(self, base: FloatInput, filter_func, pre_args: typing.Sequence, post_args: typing.Sequence):
        self._base = base
        self._filter = filter_func
        self._pre_args, self._post_args = pre_args, post_args

    def default_value(self):
        return self._filter(*self._pre_args, self._base.default_value(), *self._post_args)

    def send(self, output: FloatOutput):
        # no super call because the invoked send does it for us.
        # TODO: optimize this so that we don't redo the filtering operation for each target
        self._base.send(FilterFloatOutput(output, self._filter, self._pre_args, self._post_args))


class FilterFloatOutput(themis.codegen.RefGenerator, FloatOutput):
    def __init__(self, base: FloatOutput, filter_func, pre_args: typing.Sequence, post_args: typing.Sequence):
        super().__init__()
        self._base = base
        self._filter_ref = themis.codegen.ref(filter_func)
        self._filter = filter_func
        self._pre_args, self._post_args = pre_args, post_args
        self._pre_arg_ref = themis.codegen.ref(pre_args)
        self._post_arg_ref = themis.codegen.ref(post_args)

    def send_default_value(self, value: float):
        self._base.send_default_value(self._filter(*self._pre_args, value, *self._post_args))

    def generate_ref_code(self, ref):
        yield "def %s(fv):" % ref
        yield "\t%s(%s(*%s, fv, *%s))" % (
            self._base.get_reference(), self._filter_ref, self._pre_arg_ref, self._post_arg_ref)


def always_float(value):
    return FixedFloatInput(value)


class FixedFloatInput(FloatInput):
    def __init__(self, value: float):
        self._value = value

    def default_value(self):
        return self._value

    def send(self, output: FloatOutput):
        super(FixedFloatInput, self).send(output)
        # no changes, so we don't bother doing anything with it!


class CombinedFloatOutput(FloatOutput):
    def __init__(self, a: FloatOutput, b: FloatOutput):
        self._a, self._b = a, b
        self._ref = "combine%d" % themis.codegen.next_uid()
        themis.codegen.add_code("def %s(fv):\n\t%s(fv)\n\t%s(fv)" % (self._ref, a.get_reference(), b.get_reference()))

    def get_reference(self) -> str:
        return self._ref

    def send_default_value(self, value: float):
        self._a.send_default_value(value)
        self._b.send_default_value(value)
