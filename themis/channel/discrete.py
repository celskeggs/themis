import string
import typing

import themis.channel.event
import themis.codegen
import themis.cgen

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
    def __init__(self, instant: themis.cgen.Instant, discrete_type: Discrete):
        assert isinstance(instant, themis.cgen.Instant)
        assert isinstance(discrete_type, Discrete)
        self._instant = instant
        self.discrete_type = discrete_type
        self._sets = {}

    def get_ref(self) -> themis.cgen.Instant:
        return self._instant

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def set_event(self, value: str) -> "themis.channel.event.EventOutput":
        assert value in self.discrete_type
        if value not in self._sets:
            value_int = self.discrete_type.numeric(value)

            instant = themis.cgen.Instant(None)
            instant.invoke(self.get_ref(), value_int)
            self._sets[value] = themis.channel.event.EventOutput(instant)
        return self._sets[value]


class DiscreteInput:
    def __init__(self, instant: themis.cgen.Instant, default_value: str, discrete_type: Discrete):
        assert isinstance(instant, themis.cgen.Instant)
        self._instant = instant
        assert isinstance(discrete_type, Discrete)
        self.discrete_type = discrete_type
        assert default_value in discrete_type
        self._default_value = default_value

    def send(self, output: DiscreteOutput) -> None:
        assert self.discrete_type == output.discrete_type
        # TODO: DEFAULT VALUE
        self._instant.invoke(output.get_ref(), themis.cgen.Param)

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def is_value(self, value: str) -> "themis.channel.boolean.BooleanInput":
        value_int = self.discrete_type.numeric(value)
        instant = themis.cgen.Instant(bool)
        self._instant.operator_transform("==", instant, themis.cgen.Param, value_int)
        return themis.channel.boolean.BooleanInput(instant, self._default_value == value_int)


def discrete_cell(default_value: str, discrete_type: Discrete) -> typing.Tuple[DiscreteOutput, DiscreteInput]:
    assert isinstance(discrete_type, Discrete)
    assert default_value in discrete_type
    instant = themis.cgen.Instant(int)
    return DiscreteOutput(instant, discrete_type), DiscreteInput(instant, default_value, discrete_type)


def always_discrete(value: str, discrete_type: Discrete):
    return discrete_cell(value, discrete_type)[1]
