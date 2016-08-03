import abc
import importlib
import typing
import themis.util


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
    def __init__(self):
        self._uid = get_context().next_uid()

    @abc.abstractmethod
    def generate_expr(self) -> str:
        pass

    def generate_code(self):
        return "ref_%d = %s" % self.generate_expr()

    def get_reference(self):
        return "ref_%d" % self._uid


class LambdaGenerator(RefGenerator):
    def __init__(self, code, kwargs):
        super().__init__()
        self._code = code
        self._kwargs = {key: get_context().generate(value) for key, value in kwargs.items()}

    def get_imports(self) -> typing.Sequence[str]:
        return []

    def generate_expr(self) -> str:
        keywords = list(self._kwargs.keys())
        return "(lambda %s: %s)(%s)" % (", ".join(keywords), self._code,
                                        ", ".join(self._kwargs[keyword].get_reference() for keyword in keywords))


class TupleGenerator(Generator):
    def __init__(self, data: tuple):
        self._data = [get_context().generate(elem) for elem in data]

    def get_imports(self):
        return []

    def generate_code(self):
        return ""

    def get_reference(self):
        return "(%s)" % ", ".join(data.get_reference() for data in self._data)


class MutatorGenerator(RefGenerator):
    def __init__(self, defaults: tuple):
        super().__init__()
        self._defaults = [get_context().generate(default) for default in defaults]

    def get_imports(self):
        return []

    def generate_expr(self):
        return "[%s]" % ", ".join(default.get_reference() for default in self._defaults)


class GenerationContext:
    _context_param = themis.util.Parameter(None)

    def __init__(self):
        self._next_uid = 0
        self._init_funcs = []
        self._generation_map = {}
        self._properties = {}

    def get_prop_init(self, key, default_producer):
        if key not in self._properties:
            self._properties[key] = default_producer()
        return self._properties[key]

    def get_prop(self, key, default=None):
        return self._properties.get(key, default)

    def set_prop(self, key, value):
        self._properties[key] = value

    def _generate(self, data):
        if isinstance(data, Generator):
            return data
        elif callable(data):
            return CallableGenerator(data)  # not guaranteed to work
        elif type(data) == int or type(data) == float or type(data) == str:
            return ReprGenerator(data)
        elif type(data) == tuple:
            return TupleGenerator(data)
        else:
            raise Exception("Cannot be encoded: %s" % (data,))

    def generate(self, value):
        if isinstance(value, Generator):
            return value
        if value not in self._generation_map:
            self._generation_map[value] = self._generate(value)
        return self._generation_map[value]

    def next_uid(self):
        uid = self._next_uid
        self._next_uid += 1
        return uid

    def register_init(self, func: typing.Union[typing.Callable[[], None], Generator]) -> None:
        self._init_funcs.append(self.generate(func))

    @classmethod
    def get_context(cls) -> "GenerationContext":
        out = GenerationContext._context_param.get()
        if out is None:
            raise Exception("Attempt to use contextualized code without a context!")
        return out

    def enter(self):
        return GenerationContext._context_param.parameterize(self)


get_context = GenerationContext.get_context


def gen_lambda(lambda_code, **kwargs) -> Generator:
    return LambdaGenerator(lambda_code, kwargs)


def build_mixer(default_values, function, extra_arguments):
    mutator = MutatorGenerator(default_values)
    setters = [gen_lambda("lambda value: (mut.__setitem__(i, value), function(*mut, *args)) and None", mut=mutator, i=i,
                          function=function, args=extra_arguments) for i, value in enumerate(default_values)]
    return setters
