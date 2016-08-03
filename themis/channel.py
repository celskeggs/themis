import typing
import abc
import themis.codegen
import themis.exec.filters


def always(value):
    if isinstance(value, (int, float)):
        return FixedFloatInput(value)
    elif isinstance(value, bool):
        return FixedBooleanInput(value)
    else:
        raise TypeError("Invalid always type: %s" % value)


class EventInput(abc.ABC):
    @abc.abstractmethod
    def send(self, output: "EventOutput") -> None:
        pass


class EventOutput(abc.ABC):
    @abc.abstractmethod
    def generate_exec_event(self) -> themis.codegen.Generator:
        pass


class Event(EventInput, EventOutput):
    def __init__(self):
        self._targets = []

    def send(self, target: EventOutput):
        self._targets.append(target)

    def generate_exec_event(self) -> themis.codegen.Generator:
        return DispatchGenerator(self._targets, "")


class BooleanInput(abc.ABC):
    @abc.abstractmethod
    def send(self, output: "BooleanOutput") -> None:
        # must call output.send_default_value with the same value as default_value() would return
        pass

    @abc.abstractmethod
    def default_value(self):
        pass


class BooleanOutput(abc.ABC):
    @abc.abstractmethod
    def generate_exec_bool(self) -> themis.codegen.Generator:
        pass

    @abc.abstractmethod
    def send_default_value(self, value: bool):
        pass


class Boolean(BooleanInput, BooleanOutput):
    def __init__(self, value=False):
        self._default_value = value
        self._default_value_queried = False
        self._targets = []

    def default_value(self):
        self._default_value_queried = True
        return self._default_value

    def send(self, target: BooleanOutput):
        target.send_default_value(self.default_value())
        self._targets.append(target)

    def send_default_value(self, value: bool):
        if value != self._default_value:
            assert not self._default_value_queried, "Default value changed after usage!"

    def generate_exec_bool(self) -> themis.codegen.Generator:
        return DispatchGenerator(self._targets, "bool_value")


class FloatInput(abc.ABC):
    @abc.abstractmethod
    def send(self, output: "FloatOutput") -> None:
        # must call output.send_default_value with the same value as default_value() would return
        pass

    @abc.abstractmethod
    def default_value(self):
        pass

    def filter(self, filter_func: typing.Callable[..., float], *args) -> "FloatInput":
        return FilterFloatInput(self, filter_func, args)

    def operate(self, filter_func: typing.Callable[..., float], other: "FloatInput", *args) -> "FloatInput":
        return OperateFloatInput((self, other), filter_func, args)

    def deadzone(self, zone: float) -> "FloatInput":
        return self.filter(themis.exec.filters.deadzone, zone)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return self.filter(themis.exec.filters.multiply, other)
        elif isinstance(other, FloatInput):
            return self.operate(themis.exec.filters.multiply, other)


class FloatOutput(abc.ABC):
    @abc.abstractmethod
    def generate_exec_float(self) -> themis.codegen.Generator:
        pass

    @abc.abstractmethod
    def send_default_value(self, value: float):
        pass


class Float(FloatInput, FloatOutput):
    def __init__(self, value=0.0):
        self._default_value = value
        self._default_value_queried = False
        self._targets = []

    def default_value(self):
        self._default_value_queried = True
        return self._default_value

    def send(self, target: FloatOutput):
        target.send_default_value(self.default_value())
        self._targets.append(target)

    def send_default_value(self, value: float):
        if value != self._default_value:
            assert not self._default_value_queried, "Default value changed after usage!"

    def generate_exec_float(self) -> themis.codegen.Generator:
        return DispatchGenerator(self._targets, "float_value")


class DispatchGenerator(themis.codegen.RefGenerator):
    # dispatch_targets is explicitly designed to be mutated! at least, up until the point that we start generating code.
    def __init__(self, dispatch_targets: typing.List[themis.codegen.Generator], arg_list="*args"):
        super().__init__()
        self._targets = dispatch_targets
        self._args = arg_list

    def get_imports(self):
        return []

    def generate_expr(self) -> str:
        assert all(isinstance(target, themis.codegen.Generator) for target in self._targets)
        expressions = ["%s(%s)" % (target, self._args) for target in self._targets]
        return "lambda %s: (%s) and None" % (self._args, ", ".join(expressions))


class FilterFloatInput(FloatInput):
    def __init__(self, base: FloatInput, filter_func: typing.Callable[..., float], args: typing.Sequence):
        self._base = base
        self._filter = filter_func
        self._args = args

    def default_value(self):
        return self._filter(self._base.default_value(), *self._args)

    def send(self, output: FloatOutput):
        self._base.send(FilterFloatOutput(output, self._filter, self._args))


class FilterFloatOutput(FloatOutput):
    def __init__(self, base: FloatOutput, filter_func: typing.Callable[..., float], args: typing.Sequence):
        self._base = base
        self._filter = filter_func
        self._args = args

    def send_default_value(self, value: float):
        self._base.send_default_value(self._filter(value, *self._args))

    def generate_exec_float(self) -> themis.codegen.Generator:
        return themis.codegen.gen_lambda("lambda value: target(filter(value, *args))",
                                         target=self._base.generate_exec_float(), filter=self._filter, args=self._args)


class OperationMixer:
    def __init__(self, inputs: typing.Sequence[FloatInput], output: FloatOutput,
                 filter_func: typing.Callable[..., float], args: typing.Sequence):
        default_values = [input.default_value() for input in inputs]
        setters = themis.codegen.build_mixer(default_values, themis.exec.filters.operator, (
            output.generate_exec_float(), filter_func, args))
        output.send_default_value(filter_func(*[inp.default_value() for inp in inputs], *args))
        for i, input in enumerate(inputs):
            input.send(themis.channelgen.ExecEventOutput(themis.codegen.get_context().generate(setters[i])))


class FixedFloatInput(FloatInput):
    def __init__(self, value: float):
        self._value = value

    def default_value(self):
        return self._value

    def send(self, output: "FloatOutput"):
        output.send_default_value(self._value)


class ExecEventOutput(EventOutput):
    def __init__(self, target: themis.codegen.Generator):
        self._target = target

    def generate_exec_event(self) -> themis.codegen.Generator:
        return self._target


class ExecEventInput(EventInput):
    def __init__(self, registrar: themis.codegen.Generator):
        self._registrar = registrar

    def send(self, target: EventOutput):
        themis.codegen.get_context().register_init(
            themis.codegen.gen_lambda("lambda: registrar(callback)", registrar=self._registrar,
                                      callback=target.generate_exec_event()))
