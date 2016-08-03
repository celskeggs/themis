import abc
import importlib

import themis.util


class GenerationContext:
    _context_param = themis.util.Parameter(None)

    def __init__(self):
        self._next_uid = 0
        self._imports = []
        self._output = []
        self._output_generators = []
        self._properties = {}

    def add_import(self, module: str) -> None:
        if module not in self._imports:
            self._imports.append(module)

    def add_code(self, text: str) -> None:
        self._output += text.split("\n")

    def add_code_generator(self, gen):
        self._output_generators.append(gen)

    def generate_code(self):
        out = ["import %s" % imp for imp in self._imports]
        out.extend(self._output)
        for gen in self._output_generators:
            out.extend(gen())
        return out

    def get_prop_init(self, key, default_producer):
        if key not in self._properties:
            self._properties[key] = default_producer()
        return self._properties[key]

    def get_prop(self, key):
        return self._properties[key]

    def set_prop(self, key, value):
        self._properties[key] = value

    def next_uid(self):
        uid = self._next_uid
        self._next_uid += 1
        return uid

    @classmethod
    def get_context(cls) -> "GenerationContext":
        out = GenerationContext._context_param.get()
        if out is None:
            raise Exception("Attempt to use contextualized code without a context!")
        return out

    def enter(self):
        return GenerationContext._context_param.parameterize(self)


def next_uid():
    return GenerationContext.get_context().next_uid()


def add_import(module):
    GenerationContext.get_context().add_import(module)


def add_code(code):
    GenerationContext.get_context().add_code(code)


def add_code_generator(gen):
    GenerationContext.get_context().add_code_generator(gen)


def get_prop_init(key, default_producer):
    return GenerationContext.get_context().get_prop_init(key, default_producer)


def get_prop(key):
    return GenerationContext.get_context().get_prop(key)


class Generator(abc.ABC):
    def __init__(self):
        add_code_generator(self._generate_code)

    @abc.abstractmethod
    def _generate_code(self):
        pass


class RefGenerator(Generator):
    def __init__(self, pattern="ref%d"):
        super().__init__()
        self._ref_id = pattern % (next_uid(),)

    def _generate_code(self):
        return self.generate_ref_code(self._ref_id)

    @abc.abstractmethod
    def generate_ref_code(self, ref):
        pass

    def get_reference(self):
        return self._ref_id


def ref(obj):
    if callable(obj):
        mod, name = obj.__module__, obj.__name__
        assert getattr(importlib.import_module(mod), name, None) is obj, \
            "Function is not globally accessible - a prerequisite!"
        add_import(mod)
        return "%s.%s" % (mod, name)
    elif isinstance(obj, (int, float, bool)):
        return repr(obj)
    elif isinstance(obj, tuple):
        if len(obj) == 0:
            return "()"
        elif len(obj) == 1:
            return "(%s,)" % ref(obj[0])
        else:
            return "(%s)" % ", ".join(ref(element) for element in obj)
    raise TypeError("Cannot construct reference to: %s of type %s" % (obj, type(obj)))
