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
    def send_default_value(self, value: float):
        pass


class FloatInput(abc.ABC):
    @abc.abstractmethod
    def send(self, output: FloatOutput) -> None:
        output.send_default_value(self.default_value())

    @abc.abstractmethod
    def default_value(self) -> float:
        pass

    def filter(self, filter_ref, *args) -> "FloatInput":
        return FilterFloatInput(self, filter_ref, args)

    def deadzone(self, zone: float) -> "FloatInput":
        return self.filter(themis.exec.filters.deadzone, zone)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return self.filter(themis.exec.filters.multiply, other)
        elif isinstance(other, FloatInput):
            return self.operation(themis.exec.filters.multiply, other)
        else:
            raise NotImplemented

    def __rmul__(self, other):
        if isinstance(other, (int, float)):
            return self.filter(themis.exec.filters.multiply, other)
        elif isinstance(other, FloatInput):
            return other.operation(themis.exec.filters.multiply, self)
        else:
            raise NotImplemented


class FloatCell(themis.codegen.RefGenerator, FloatInput, FloatOutput):
    def __init__(self, value=0.0):
        super().__init__()
        self._default_value = value
        self._default_value_queried = False
        self._targets = []

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
        yield "def %s(fv: float) -> None:" % ref
        for target in self._targets:
            yield "\t%s(fv)" % target.get_reference()


class FilterFloatInput(FloatInput):
    def __init__(self, base: FloatInput, filter_func, args: typing.Sequence):
        self._base = base
        self._filter = filter_func
        self._args = args

    def default_value(self):
        return self._filter(self._base.default_value(), *self._args)

    def send(self, output: FloatOutput):
        # no super call because the invoked send does it for us.
        self._base.send(FilterFloatOutput(output, self._filter, self._args))


class FilterFloatOutput(themis.codegen.RefGenerator, FloatOutput):
    def __init__(self, base: FloatOutput, filter_func, args: typing.Sequence):
        super().__init__()
        self._base = base
        self._filter_ref = themis.codegen.ref(filter_func)
        self._filter = filter_func
        self._args = args
        self._arg_ref = themis.codegen.ref(args)

    def send_default_value(self, value: float):
        self._base.send_default_value(self._filter(value, *self._args))

    def generate_ref_code(self, ref):
        yield "def %s(fv):" % ref
        yield "\t%s(%s(fv, *%s))" % (self._base.get_reference(), self._filter_ref, self._arg_ref)


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
