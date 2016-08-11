import typing

import themis.pygen.annot
import themis.pygen.counter

PARAM_TYPES = {None: "None", bool: "bool", int: "int", float: "float"}

uid = counter.Counter()

Param = object()


class Box:
    def __init__(self, initial_value):
        self._value = initial_value
        self._box_type = type(initial_value)
        assert self._box_type is not None and self._box_type in PARAM_TYPES, \
            "Invalid initial value type: %s" % type(initial_value)
        self._box = uid.nstr("box%d")

    def _generate(self) -> str:
        return "%s = %s" % (self._box, repr(self._value))


class Instant:
    def __init__(self, param_type):
        assert param_type in PARAM_TYPES
        self._param_type = param_type
        self._param = uid.nstr("param%d")
        self._instant = uid.nstr("instant%d")
        self._calls = []
        self._referenced_modules = set()
        self._referenced_boxes = set()
        self._referenced_instants = set()

    def is_param_type(self, type_ref):
        return self._param_type == type_ref

    def _validate_type(self, arg) -> typing.Tuple[typing.Type, str]:
        assert arg is not None
        if arg is Param:
            return self._param_type, self._param
        elif isinstance(arg, Box):
            self._referenced_boxes.add(arg)
            return arg._box_type, arg._box
        elif type(arg) in PARAM_TYPES:
            return type(arg), repr(arg)
        elif hasattr(arg, "get_ref"):
            arg = arg.get_ref()
        if isinstance(arg, Instant):
            self._referenced_instants.add(arg)
            return typing.Callable[[] if arg._param_type is None else [arg._param_type], None], arg._instant
        else:
            assert False, "Invalid parameter (bad type): %s" % (arg,)

    def _validate_gen(self, arg, expected_type: typing.Type) -> str:
        arg_type, arg_value = self._validate_type(arg)
        assert expected_type is not None
        assert arg_type == expected_type, "Type mismatch: got %s but expected %s" % (arg_type, expected_type)
        return arg_value

    def invoke(self, inst: "Instant", arg=None) -> None:
        assert isinstance(inst, Instant)
        self._referenced_instants.add(inst)
        if arg is None:
            assert inst._param_type is None
            self._calls.append("%s()" % (inst._instant,))
        else:
            param_value = self._validate_gen(arg, inst._param_type)
            self._calls.append("%s(%s)" % (inst._instant, param_value))

    def set(self, box: Box, arg):
        assert isinstance(box, Box)
        param_value = self._validate_gen(arg, box._box_type)
        self._calls.append("%s = %s" % (box._box, param_value))

    def if_equal(self, comp_a, comp_b, target: "Instant", arg=None):
        assert isinstance(target, Instant)
        self._referenced_instants.add(target)
        comp_type, gen_a = self._validate_type(comp_a)
        gen_b = self._validate_gen(comp_b, comp_type)

        if target._param_type is None:
            assert arg is None
            arg_value = ""
        else:
            arg_value = self._validate_gen(arg, target._param_type)

        self._calls.append("if %s == %s:" % (gen_a, gen_b))
        self._calls.append("\t%s(%s)" % (target._instant, arg_value))

    def if_unequal(self, comp_a, comp_b, target: "Instant", arg=None):
        assert isinstance(target, Instant)
        self._referenced_instants.add(target)
        comp_type, gen_a = self._validate_type(comp_a)
        gen_b = self._validate_gen(comp_b, comp_type)

        if target._param_type is None:
            assert arg is None
            arg_value = ""
        else:
            arg_value = self._validate_gen(arg, target._param_type)

        self._calls.append("if %s != %s:" % (gen_a, gen_b))
        self._calls.append("\t%s(%s)" % (target._instant, arg_value))

    def if_else(self, comp_a, comp_b, when_true: "Instant", when_false: "Instant", arg_true=None, arg_false=None):
        assert isinstance(when_true, Instant)
        assert isinstance(when_false, Instant)
        self._referenced_instants.add(when_true)
        self._referenced_instants.add(when_false)
        comp_type, gen_a = self._validate_type(comp_a)
        gen_b = self._validate_gen(comp_b, comp_type)

        if when_true._param_type is None:
            assert arg_true is None
            arg_value_true = ""
        else:
            arg_value_true = self._validate_gen(arg_true, when_true._param_type)

        if when_false._param_type is None:
            assert arg_false is None
            arg_value_false = ""
        else:
            arg_value_false = self._validate_gen(arg_false, when_false._param_type)

        self._calls.append("if %s == %s:" % (gen_a, gen_b))
        self._calls.append("\t%s(%s)" % (when_true._instant, arg_value_true))
        self._calls.append("else:")
        self._calls.append("\t%s(%s)" % (when_false._instant, arg_value_false))

    def transform(self, filter_ref, instant_target: typing.Optional["Instant"], *args):
        if instant_target is not None:
            assert isinstance(instant_target, Instant)
            self._referenced_instants.add(instant_target)

        mod, name = themis.pygen.annot.get_global_ref(filter_ref)
        self._referenced_modules.add(mod)

        arg_types, return_type = themis.pygen.annot.get_types(filter_ref)
        assert len(arg_types) == len(args), "Argument length mismatch on %s" % filter_ref
        arg_values = [self._validate_gen(arg, param_type) for arg, param_type in zip(args, arg_types)]

        invocation = "%s.%s(%s)" % (mod, name, ", ".join(arg_values))
        if instant_target is None:
            assert return_type is None
            self._calls.append(invocation)
        else:
            assert return_type is not None
            assert return_type is instant_target._param_type
            self._calls.append("%s(%s)" % (instant_target._instant, invocation))

    def _generate(self):
        yield "def %s(%s: %s) -> None:" % (self._instant, self._param, PARAM_TYPES[self._param_type])
        if self._calls:
            if self._referenced_boxes:
                yield "\tglobal %s" % ", ".join(box._box for box in self._referenced_boxes)
            for call in self._calls:
                yield "\t%s" % (call,)
        else:
            yield "\tpass"


def _enumerate_instants(root_instant: Instant) -> typing.Set[Instant]:
    assert isinstance(root_instant, Instant)
    remaining_instants = {root_instant}
    processed_instants = set()
    while remaining_instants:
        instant = remaining_instants.pop()
        processed_instants.add(instant)
        remaining_instants.update(instant._referenced_instants)
        remaining_instants.difference_update(processed_instants)
    return processed_instants


def generate_code(root_instant: Instant):
    instants = _enumerate_instants(root_instant)
    modules = set().union(*(instant._referenced_modules for instant in instants))
    boxes = set().union(*(instant._referenced_boxes for instant in instants))
    out = ["import %s" % (module,) for module in modules]
    out += [box._generate() for box in boxes]
    for instant in instants:
        out += instant._generate()
    return "\n".join(out)
