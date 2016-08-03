import typing
import abc
import themis.codegen_inner
import themis.exec.filters


def always(value):
    if isinstance(value, (int, float)):
        return FixedFloatInput(value)
    # elif isinstance(value, bool):
    #     return FixedBooleanInput(value)
    else:
        raise TypeError("Invalid always type: %s" % value)


class EventInput(abc.ABC):
    @abc.abstractmethod
    def send(self, output: "EventOutput") -> None:
        pass


class EventOutput(abc.ABC):
    @abc.abstractmethod
    def generate_exec_event(self, context: themis.codegen_inner.InternalContext) -> themis.codegen_inner.Generator:
        pass


class Event(EventInput, EventOutput):
    def __init__(self):
        self._targets = []

    def send(self, target: EventOutput):
        self._targets.append(target)

    def generate_exec_event(self, context: themis.codegen_inner.InternalContext) -> themis.codegen_inner.Generator:
        return DispatchGenerator(context, self._targets, "")


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
    def generate_exec_bool(self, context: themis.codegen_inner.InternalContext) -> themis.codegen_inner.Generator:
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

    def generate_exec_bool(self, context: themis.codegen_inner.InternalContext) -> themis.codegen_inner.Generator:
        return DispatchGenerator(context, self._targets, "bool_value")


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
    def generate_exec_float(self, context: themis.codegen_inner.InternalContext) -> themis.codegen_inner.Generator:
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

    def generate_exec_float(self, context: themis.codegen_inner.InternalContext) -> themis.codegen_inner.Generator:
        return DispatchGenerator(context, self._targets, "float_value")


class DispatchGenerator(themis.codegen_inner.RefGenerator):
    # dispatch_targets is explicitly designed to be mutated! at least, up until the point that we start generating code.
    def __init__(self, context: themis.codegen_inner.InternalContext,
                 dispatch_targets: typing.List[themis.codegen_inner.Generator], arg_list="*args"):
        super().__init__(context)
        self._targets = dispatch_targets
        self._args = arg_list

    def get_imports(self):
        return []

    def generate_expr(self) -> str:
        assert all(isinstance(target, themis.codegen_inner.Generator) for target in self._targets)
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

    def generate_exec_float(self, context: themis.codegen_inner.InternalContext) -> themis.codegen_inner.Generator:
        return context.lambda_exec("lambda target, filter, args: lambda value: target(filter(value, *args))",
                                   self._base.generate_exec_float(context), self._filter, self._args)


class OperationMixer:
    def __init__(self, inputs: typing.Sequence[FloatInput], output: FloatOutput,
                 filter_func: typing.Callable[..., float], args: typing.Sequence):
        self._inputs = inputs
        self._filter = filter_func
        self._args = args
        self._cached_context = None
        self._cached_setters = None
        self._output = output
        output.send_default_value(self._filter(*[inp.default_value() for inp in inputs], *self._args))
        for i, input in enumerate(inputs):
            input.send(OperatePartialFloatOutput(self._finish_prepare, i))

    def _finish_prepare(self, context, i):
        if self._cached_context is None:
            self._cached_context = context
            default_values = [input.default_value() for input in self._inputs]
            self._cached_setters = context.build_mixer(
                default_values, themis.exec.filters.operator,
                (self._output.generate_exec_float(context), self._filter, self._args))
        else:
            assert self._cached_context is context
        return self._cached_setters[i]


class OperatePartialFloatOutput(FloatOutput):
    def __init__(self, generate, i):
        self._generate = generate
        self._i = i

    def send_default_value(self, value: float):
        pass  # ignore it!

    def generate_exec_float(self, context: themis.codegen_inner.InternalContext) -> themis.codegen_inner.Generator:
        return self._generate(context, self._i)


class FixedFloatInput(FloatInput):
    def __init__(self, value: float):
        self._value = value

    def default_value(self):
        return self._value

    def send(self, output: "FloatOutput"):
        output.send_default_value(self._value)
