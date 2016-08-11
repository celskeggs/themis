import themis.pygen
import themis.util
import enum


class InitPhase(enum.Enum):
    PHASE_INIT_CODE = 1
    PHASE_INIT_IO = 2
    PHASE_BEGIN = 3


class GenerationContext:
    _context_param = themis.util.Parameter(None)

    def __init__(self):
        self._initialize = themis.pygen.Instant(None)
        self._init_phases = {}
        for phase in InitPhase:
            inst = themis.pygen.Instant(None)
            self._initialize.invoke(inst)
            self._init_phases[phase] = inst
        self._properties = {}

    def add_init(self, instant: themis.pygen.Instant, phase: InitPhase, arg=None):
        self._init_phases[phase].invoke(instant, arg)

    def add_init_call(self, target, phase: InitPhase, *args):
        self._init_phases[phase].transform(target, None, *args)

    def generate_code(self):
        return themis.pygen.generate_code(self._initialize)

    def get_prop_init(self, key, default_producer):
        if key not in self._properties:
            self._properties[key] = default_producer()
        return self._properties[key]

    def get_prop(self, key):
        return self._properties[key]

    def set_prop(self, key, value):
        self._properties[key] = value

    @classmethod
    def get_context(cls) -> "GenerationContext":
        out = GenerationContext._context_param.get()
        if out is None:
            raise Exception("Attempt to use contextualized code without a context!")
        return out

    def enter(self):
        return GenerationContext._context_param.parameterize(self)


def add_init(instant: themis.pygen.Instant, phase: InitPhase, arg=None):
    GenerationContext.get_context().add_init(instant, phase, arg)


def add_init_call(target, phase: InitPhase, *args):
    GenerationContext.get_context().add_init_call(target, phase, *args)


def get_prop_init(key, default_producer):
    return GenerationContext.get_context().get_prop_init(key, default_producer)


def get_prop(key):
    return GenerationContext.get_context().get_prop(key)


def generate_code():
    return GenerationContext.get_context().generate_code()
