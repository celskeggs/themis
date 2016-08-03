import themis.codegen
import enum


class Phase(enum.Enum):
    PHASE_INIT_CODE = 1
    PHASE_INIT_IO = 2
    PHASE_BEGIN = 3


def _init_inits():
    themis.codegen.add_code_generator(_init_gen)
    return {phase: [] for phase in Phase}


def _init_gen():
    inits = themis.codegen.get_prop(add_init_call)
    yield "def run():"
    for phase in Phase:
        yield "\t# %s" % phase.name
        for f, args in inits[phase]:
            yield "\t%s(*%s)" % (f, args)


def add_init_call(call_ref: str, phase: Phase, args: tuple=()):
    inits = themis.codegen.get_prop_init(add_init_call, _init_inits)
    inits[phase].append((call_ref, themis.codegen.ref(args)))
