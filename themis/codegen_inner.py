import abc
import importlib
import typing


class Generator(abc.ABC):
    @abc.abstractmethod
    def get_imports(self) -> typing.Sequence[str]:
        pass

    @abc.abstractmethod
    def generate_code(self) -> str:
        pass

    @abc.abstractmethod
    def get_reference(self) -> str:
        pass


class CallableGenerator(Generator):
    def __init__(self, target_method: typing.Callable):
        self._target_method = target_method
        module = importlib.import_module(self._target_method.__module__)
        assert hasattr(module, self._target_method.__name__)

    def get_imports(self) -> typing.Sequence[str]:
        return [self._target_method.__module__]

    def generate_code(self) -> str:
        return ""

    def get_reference(self) -> str:
        return "%s.%s" % (self._target_method.__module__, self._target_method.__name__)


class ReprGenerator(Generator):
    def __init__(self, data):
        self._data = data

    def get_imports(self) -> typing.Sequence[str]:
        return []

    def generate_code(self) -> str:
        return ""

    def get_reference(self) -> str:
        return repr(self._data)


class RefGenerator(Generator):
    def __init__(self, context: "InternalContext"):
        self._uid = context.next_uid()

    @abc.abstractmethod
    def generate_expr(self) -> str:
        pass

    def generate_code(self):
        return "ref_%d = %s" % self.generate_expr()

    def get_reference(self):
        return "ref_%d" % self._uid


class LambdaGenerator(RefGenerator):
    def __init__(self, context: "InternalContext", code, args):
        super().__init__(context)
        self._code = code
        self._args = [context.generate(arg) for arg in args]

    def get_imports(self) -> typing.Sequence[str]:
        return []

    def generate_expr(self) -> str:
        return "(%s)(%s)" % (self._code, ", ".join(arg.get_reference() for arg in self._args))


class TupleGenerator(Generator):
    def __init__(self, context: "InternalContext", data: tuple):
        self._data = [context.generate(elem) for elem in data]

    def get_imports(self):
        return []

    def generate_code(self):
        return ""

    def get_reference(self):
        return "(%s)" % ", ".join(data.get_reference() for data in self._data)


class MutatorGenerator(RefGenerator):
    def __init__(self, context: "InternalContext", defaults: tuple):
        super().__init__(context)
        self._defaults = [context.generate(default) for default in defaults]

    def get_imports(self):
        return []

    def generate_expr(self):
        return "[%s]" % ", ".join(default.get_reference() for default in self._defaults)


class InternalContext:
    def __init__(self):
        self._init_funcs = []
        self._generation_map = {}
        self._next_uid = 0

    def next_uid(self):
        uid = self._next_uid
        self._next_uid += 1
        return uid

    def register_init(self, func: typing.Callable[[], None]) -> None:
        self._init_funcs.append(func)

    def lambda_exec(self, lambda_code, *args) -> Generator:  # TODO: make interface cleaner
        return LambdaGenerator(self, lambda_code, args)

    def _generate(self, data):
        if isinstance(data, Generator):
            return data
        elif callable(data):
            return CallableGenerator(data)  # not guaranteed to work
        elif type(data) == int or type(data) == float or type(data) == str:
            return ReprGenerator(data)
        elif type(data) == tuple:
            return TupleGenerator(self, data)
        else:
            raise Exception("Cannot be encoded: %s" % (data,))

    def generate(self, value):
        if isinstance(value, Generator):
            return value
        if value not in self._generation_map:
            self._generation_map[value] = self._generate(value)
        return self._generation_map[value]

    def build_mixer(self, default_values, function, extra_arguments):
        mutator = MutatorGenerator(self, default_values)
        setters = [self.lambda_exec(
            "lambda mutator, i, function, extra_arguments: lambda value: (mutator.__setitem__(i, value), function(*mutator, *extra_arguments)) and None",
            mutator, i, function, extra_arguments) for i, value in enumerate(default_values)]
        return setters
