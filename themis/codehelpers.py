import themis.codegen
import themis.channel


class EventWrapper(themis.channel.EventOutput):
    def __init__(self, ref: str):
        self._ref = ref

    def get_reference(self) -> str:
        return self._ref


def poll_float(event: themis.channel.EventInput, poll_func, args) -> themis.channel.FloatInput:
    f = themis.channel.FloatCell()
    newref = "pollf%d" % themis.codegen.next_uid()
    themis.codegen.add_code("def %s():\n\t%s(%s(*%s))" %
                            (newref, f.get_reference(), themis.codegen.ref(poll_func), themis.codegen.ref(args)))
    event.send(EventWrapper(newref))
    return f


def poll_boolean(event: themis.channel.EventInput, poll_func, args) -> themis.channel.BooleanInput:
    f = themis.channel.BooleanCell()
    newref = "pollb%d" % themis.codegen.next_uid()
    themis.codegen.add_code("def %s():\n\t%s(%s(*%s))" %
                            (newref, f.get_reference(), themis.codegen.ref(poll_func), themis.codegen.ref(args)))
    event.send(EventWrapper(newref))
    return f
