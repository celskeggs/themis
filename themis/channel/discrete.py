import abc
import typing
import themis.channel.event
import themis.codegen
import enum
import string

__all__ = ["DiscreteOutput", "DiscreteInput", "discrete_cell", "always_discrete", "Discrete"]

VALID_ENUM_CHARS = string.ascii_uppercase + "_"


class Discrete:
    def __init__(self, options: str):
        self._opts = options.split(" ")
        for option in self._opts:
            assert all(c in VALID_ENUM_CHARS for c in option)
            setattr(self, option, option)

    def __iter__(self):
        return iter(self._opts)

    def numeric(self, option: str):
        return self._opts.index(option)


class DiscreteOutput:
    def __init__(self, reference: str, discrete_type: Discrete):
        assert isinstance(reference, str)
        assert isinstance(discrete_type, Discrete)
        self._ref = reference
        self.discrete_type = discrete_type
        self._sets = {}

    def get_discrete_ref(self) -> str:
        return self._ref

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def set_event(self, value: str) -> "themis.channel.event.EventOutput":
        assert value in self.discrete_type
        if value not in self._sets:
            value_int = self.discrete_type.numeric(value)

            @themis.channel.event.event_build
            def update(ref: str):
                yield "%s(%s)" % (self.get_discrete_ref(), value_int)

            self._sets[value] = update
        return self._sets[value]


class DiscreteInput:
    def __init__(self, targets: list, discrete_type: Discrete):
        assert isinstance(targets, list)
        self._targets = targets
        assert isinstance(discrete_type, Discrete)
        self.discrete_type = discrete_type

    def send(self, output: DiscreteOutput) -> None:
        assert self.discrete_type == output.discrete_type
        self._targets.append(output.get_discrete_ref())

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def is_value(self, value: str) -> "themis.channel.boolean.BooleanInput":
        value_int = self.discrete_type.numeric(value)
        cell_out, cell_in = themis.channel.boolean.boolean_cell(False)  # TODO: default value

        @discrete_build(self.discrete_type)
        def update(ref: str):
            yield "%s(value == %s)" % (cell_out.get_boolean_ref(), value_int)

        self.send(update)
        return cell_in


def discrete_build(discrete_type: Discrete):
    assert isinstance(discrete_type, Discrete)

    def bound_build(body_gen) -> DiscreteOutput:
        def gen(ref: str):
            yield "def %s(value: int) -> None:" % ref
            for line in body_gen(ref):
                yield "\t%s" % (line,)

        return DiscreteOutput(themis.codegen.add_code_gen_ref(gen), discrete_type)

    return bound_build


def discrete_cell(default_value: str, discrete_type: Discrete) -> typing.Tuple[DiscreteOutput, DiscreteInput]:
    assert isinstance(discrete_type, Discrete)
    assert default_value in discrete_type
    # TODO: use default_value
    targets = []

    @discrete_build(discrete_type)
    def dispatch(ref: str):
        if targets:
            for target in targets:
                yield "%s(value)" % (target,)
        else:
            yield "pass"

    return dispatch, DiscreteInput(targets, discrete_type)


def always_discrete(value: str, discrete_type: Discrete):
    return discrete_cell(value, discrete_type)[1]
