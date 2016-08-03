import abc

import themis.codegen

__all__ = ["EventOutput", "EventInput", "EventCell"]


class EventOutput(abc.ABC):
    @abc.abstractmethod
    def get_reference(self) -> str:
        pass


class EventInput(abc.ABC):
    def send(self, output: EventOutput) -> None:
        # split up entirely for consistency with BooleanInput and FloatInput
        self._send(output)

    @abc.abstractmethod
    def _send(self, output: EventOutput) -> None:
        pass


class EventCell(themis.codegen.RefGenerator, EventInput, EventOutput):
    def __init__(self):
        super().__init__()
        self._targets = []

    def _send(self, target: EventOutput):
        self._targets.append(target)

    def generate_ref_code(self, ref):
        yield "def %s() -> None:" % ref
        for target in self._targets:
            yield "\t%s()" % target.get_reference()
