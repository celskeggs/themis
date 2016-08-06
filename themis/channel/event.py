import typing

import themis.codegen

__all__ = ["EventOutput", "EventInput", "event_cell"]


class EventOutput:
    def __init__(self, reference: str):
        assert isinstance(reference, str)
        self._ref = reference

    def get_event_ref(self) -> str:
        return self._ref

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def when(self, event: "EventInput") -> None:
        event.send(self)


class EventInput:
    def __init__(self, targets: list):
        assert isinstance(targets, list)
        self._targets = targets

    def send(self, output: EventOutput) -> None:
        assert isinstance(output, EventOutput)
        self._targets.append(output.get_event_ref())

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")


def event_build(body_gen) -> EventOutput:
    def gen(ref: str):
        yield "def %s() -> None:" % ref
        for line in body_gen(ref):
            yield "\t%s" % (line,)

    return EventOutput(themis.codegen.add_code_gen_ref(gen))


def event_cell() -> typing.Tuple[EventOutput, EventInput]:
    targets = []

    @event_build
    def dispatch(ref: str):
        if targets:
            for target in targets:
                yield "%s()" % (target,)
        else:
            yield "pass"

    return dispatch, EventInput(targets)
