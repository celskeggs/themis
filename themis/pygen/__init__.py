import typing

import themis.pygen.annot
import themis.pygen.counter
import themis.pygen.optimizer
import themis.pygen.templates

PARAM_TYPES = {None: "None", bool: "bool", int: "int", float: "float"}

uid = counter.Counter()

Param = object()

__all__ = ["Box", "Instant", "generate_code", "Param"]


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
        if param_type is not None:
            self._param = uid.nstr("param%d")
        self._uid = uid.next()
        self._instant = "instant%d" % self._uid
        self._body = []
        self._referenced_modules = set()
        self._referenced_instants = set()

    def is_param_type(self, type_ref):
        return self._param_type == type_ref

    def is_empty(self):
        return not self._body

    def _validate_type(self, arg) -> typing.Tuple[typing.Type, str]:
        assert arg is not None
        if arg is Param:
            return self._param_type, self._param
        elif isinstance(arg, Box):
            return arg._box_type, arg._box
        elif type(arg) in PARAM_TYPES:
            return type(arg), repr(arg)
        elif hasattr(arg, "get_ref"):
            arg = arg.get_ref()
        if isinstance(arg, Instant):
            self._referenced_instants.add(arg)
            return typing.Callable[[] if arg._param_type is None else [arg._param_type], None], arg
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
            self._body.append((templates.invoke_nullary, inst))
        else:
            param_value = self._validate_gen(arg, inst._param_type)
            self._body.append((templates.invoke_unary, inst, param_value))

    def set(self, box: Box, arg):
        assert isinstance(box, Box)
        param_value = self._validate_gen(arg, box._box_type)
        self._body.append((templates.set, box, param_value))

    def if_equal(self, comp_a, comp_b, target: "Instant", arg=None):
        assert isinstance(target, Instant)
        self._referenced_instants.add(target)
        comp_type, gen_a = self._validate_type(comp_a)
        gen_b = self._validate_gen(comp_b, comp_type)

        if target._param_type is None:
            assert arg is None
            invocation = (templates.invoke_nullary, target)
        else:
            arg_value = self._validate_gen(arg, target._param_type)
            invocation = (templates.invoke_unary, target, arg_value)

        self._body.append((templates.if_then, (templates.equals, gen_a, gen_b),
                           invocation))

    def if_unequal(self, comp_a, comp_b, target: "Instant", arg=None):
        assert isinstance(target, Instant)
        self._referenced_instants.add(target)
        comp_type, gen_a = self._validate_type(comp_a)
        gen_b = self._validate_gen(comp_b, comp_type)

        if target._param_type is None:
            assert arg is None
            invocation = (templates.invoke_nullary, target)
        else:
            arg_value = self._validate_gen(arg, target._param_type)
            invocation = (templates.invoke_unary, target, arg_value)

        self._body.append((templates.if_then, (templates.not_equals, gen_a, gen_b),
                           invocation))

    def if_else(self, comp_a, comp_b, when_true: "Instant", when_false: "Instant", arg_true=None, arg_false=None):
        assert isinstance(when_true, Instant)
        assert isinstance(when_false, Instant)
        self._referenced_instants.add(when_true)
        self._referenced_instants.add(when_false)
        comp_type, gen_a = self._validate_type(comp_a)
        gen_b = self._validate_gen(comp_b, comp_type)

        if when_true._param_type is None:
            assert arg_true is None
            call_true = (templates.invoke_nullary, when_true)
        else:
            call_true = (templates.invoke_unary, when_true, self._validate_gen(arg_true, when_true._param_type))

        if when_false._param_type is None:
            assert arg_false is None
            call_false = (templates.invoke_nullary, when_false)
        else:
            call_false = (templates.invoke_unary, when_false, self._validate_gen(arg_false, when_false._param_type))

        if gen_b == "True":
            self._body.append((templates.if_else, gen_a, call_true, call_false))
        else:
            self._body.append((templates.if_else, (templates.equals, gen_a, gen_b), call_true, call_false))

    def transform(self, filter_ref, instant_target: typing.Optional["Instant"], *args):
        if instant_target is not None:
            assert isinstance(instant_target, Instant)
            self._referenced_instants.add(instant_target)

        mod, name = themis.pygen.annot.get_global_ref(filter_ref)
        self._referenced_modules.add(mod)

        arg_types, return_type = themis.pygen.annot.get_types(filter_ref)
        assert len(arg_types) == len(args), "Argument length mismatch on %s" % filter_ref
        arg_values = [self._validate_gen(arg, param_type) for arg, param_type in zip(args, arg_types)]

        invocation = (templates.invoke_poly, "%s.%s" % (mod, name), arg_values)
        if instant_target is None:
            assert return_type is None
        else:
            assert return_type is not None
            assert return_type is instant_target._param_type
            invocation = (templates.invoke_unary, instant_target, invocation)
        self._body.append(invocation)

    def _walk_refed_boxes(self, tree, out: set) -> None:
        if type(tree) in (list, tuple):
            for subtree in tree:
                self._walk_refed_boxes(subtree, out)
        elif isinstance(tree, Box):
            out.add(tree)

    def get_referenced_boxes(self) -> set:
        sum_set = set()
        self._walk_refed_boxes(self._body, sum_set)
        return sum_set

    def _generate(self):
        if self._param_type is None:
            yield "def %s() -> None:" % (self._instant,)
        else:
            yield "def %s(%s: %s) -> None:" % (self._instant, self._param, PARAM_TYPES[self._param_type])
        if self._body:
            boxes = self.get_referenced_boxes()
            if boxes:
                yield "\tglobal %s" % ", ".join(box._box for box in boxes)
            for chunk in self._body:
                for line in templates.apply(chunk).split("\n"):
                    yield "\t%s" % (line,)
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
    assert root_instant.is_param_type(None)

    # find all involved instants, imports, and boxes
    instants = _enumerate_instants(root_instant)
    modules = set().union(*(instant._referenced_modules for instant in instants))

    # optimize the setup - after we find everything, to avoid losing reference info
    root_instant, instants = optimizer.optimize(root_instant, instants)

    boxes = set().union(*(instant.get_referenced_boxes() for instant in instants))

    # generate code
    out = ["import %s" % (module,) for module in modules]
    out += [box._generate() for box in boxes]
    for instant in sorted(instants, key=lambda instant: instant._uid):
        out += instant._generate()
    out += ["%s()" % root_instant._instant]

    return "\n".join(out)
