import abc

import themis.codegen

__all__ = ["BooleanOutput", "BooleanInput", "BooleanCell", "always_boolean"]


class BooleanOutput(abc.ABC):
    @abc.abstractmethod
    def get_reference(self) -> str:
        pass

    @abc.abstractmethod
    def send_default_value(self, value: bool):
        pass


class BooleanInput(abc.ABC):
    def send(self, output: BooleanOutput) -> None:
        output.send_default_value(self.default_value())
        self._send(output)

    @abc.abstractmethod
    def _send(self, output: BooleanOutput) -> None:
        pass

    @abc.abstractmethod
    def default_value(self) -> bool:
        pass


class BooleanCell(themis.codegen.RefGenerator, BooleanInput, BooleanOutput):
    def __init__(self, value=False):
        super().__init__()
        self._default_value = value
        self._default_value_queried = False
        self._targets = []

    def default_value(self):
        self._default_value_queried = True
        return self._default_value

    def _send(self, target: BooleanOutput):
        self._targets.append(target)

    def send_default_value(self, value: bool):
        if value != self._default_value:
            assert not self._default_value_queried, "Default value changed after usage!"

    def generate_ref_code(self, ref):
        yield "def %s(bv: bool) -> None:" % ref
        for target in self._targets:
            yield "\t%s(bv)" % target.get_reference()



def always_boolean(value):
    return FixedBooleanInput(value)


class FixedBooleanInput(BooleanInput):
    def __init__(self, value: bool):
        self._value = value

    def default_value(self):
        return self._value

    def send(self, output: BooleanOutput):
        super(FixedBooleanInput, self).send(output)
        # no changes, so we don't bother doing anything with it!
