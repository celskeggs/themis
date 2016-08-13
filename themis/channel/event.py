import typing

import themis.cgen
import themis.codegen

__all__ = ["EventOutput", "EventInput", "event_cell"]


class EventOutput:
    def __init__(self, instant: themis.cgen.Instant):
        assert isinstance(instant, themis.cgen.Instant)
        assert instant.is_param_type(None)
        self._instant = instant

    def get_ref(self) -> themis.cgen.Instant:
        return self._instant

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def when(self, event: "EventInput") -> None:
        event.send(self)


class EventInput:
    def __init__(self, instant: themis.cgen.Instant):
        assert isinstance(instant, themis.cgen.Instant)
        assert instant.is_param_type(None)
        self._instant = instant

    def get_instant(self) -> themis.cgen.Instant:
        return self._instant

    def send(self, output: EventOutput) -> None:
        assert isinstance(output, EventOutput)
        self._instant.invoke(output.get_ref())

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")


def event_cell() -> typing.Tuple[EventOutput, EventInput]:
    instant = themis.cgen.Instant(None)
    return EventOutput(instant), EventInput(instant)
