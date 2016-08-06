import abc
import themis.channel.event
import themis.codegen
import enum

__all__ = ["DiscreteOutput", "DiscreteInput", "DiscreteCell", "always_discrete"]


class DiscreteOutput(abc.ABC):
    def __init__(self, enum_type: enum.Enum):
        super().__init__(enum_type)
        self.discrete_type = enum_type
        self._sets = {}

    @abc.abstractmethod
    def get_reference(self) -> str:
        pass

    @abc.abstractmethod
    def send_default_value(self, value: enum.Enum):
        pass

    def set_event(self, value: enum.Enum) -> "themis.channel.event.EventOutput":
        assert value in self.discrete_type
        if value not in self._sets:
            import themis.codehelpers
            ref = "set_%s_%s" % (value.value, self.get_reference())
            themis.codegen.add_code("def %s():\n\t%s(%s)" % (ref, self.get_reference(), value.value))
            self._sets[value] = themis.codehelpers.EventWrapper(ref)
        return self._sets[value]


class DiscreteInput(abc.ABC):
    def __init__(self, enum_type: enum.Enum):
        # TODO: verify enum types against each other in appropriate cases
        super().__init__(enum_type)
        self.discrete_type = enum_type
        self._press, self._release = None, None

    def send(self, output: DiscreteOutput) -> None:
        output.send_default_value(self.default_value())
        self._send(output)

    @abc.abstractmethod
    def _send(self, output: DiscreteOutput) -> None:
        pass

    @abc.abstractmethod
    def default_value(self) -> enum.Enum:
        pass


class DiscreteCell(themis.codegen.RefGenerator, DiscreteInput, DiscreteOutput):
    def __init__(self, value: enum.Enum, enum_type: enum.Enum):
        super().__init__(enum_type)
        assert value in enum_type
        self._default_value = value
        self._default_value_queried = False
        self._targets = []

    def default_value(self):
        self._default_value_queried = True
        return self._default_value

    def _send(self, target: DiscreteOutput):
        self._targets.append(target)

    def send_default_value(self, value: enum.Enum):
        if value != self._default_value:
            assert not self._default_value_queried, "Default value changed after usage!"

    def generate_ref_code(self, ref):
        yield "value_%s = %s" % (ref, self._default_value.value)
        yield "def %s(bv: bool) -> None:" % ref
        yield "\tglobals value_%s" % ref
        yield "\tif bv == value_%s: return" % ref
        yield "\tvalue_%s = bv" % ref
        for target in self._targets:
            yield "\t%s(bv)" % target.get_reference()


def always_discrete(value, enum_type: enum.Enum):
    return FixedDiscreteInput(value, enum_type)


class FixedDiscreteInput(DiscreteInput):
    def __init__(self, value: enum.Enum, enum_type: enum.Enum):
        super().__init__(enum_type)
        self._value = value

    def default_value(self):
        return self._value

    def send(self, output: DiscreteOutput):
        super().send(output)
        # no changes, so we don't bother doing anything with it!
