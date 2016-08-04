import themis.codegen
import themis.channel


class EventWrapper(themis.channel.EventOutput):
    def __init__(self, ref: str):
        self._ref = ref

    def get_reference(self) -> str:
        return self._ref


class FloatWrapper(themis.channel.FloatOutput):
    def __init__(self, ref: str):
        self._ref = ref

    def get_reference(self) -> str:
        return self._ref

    def send_default_value(self, value: float):
        pass  # TODO: handle default value correctly


class BooleanWrapper(themis.channel.BooleanOutput):
    def __init__(self, ref: str):
        self._ref = ref

    def get_reference(self) -> str:
        return self._ref

    def send_default_value(self, value: float):
        pass  # TODO: handle default value correctly


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


def push_float(update_func, extra_args) -> themis.channel.FloatOutput:
    newref = "pushf%d" % themis.codegen.next_uid()
    themis.codegen.add_code("def %s(fv):\n\t%s(fv, *%s)" %
                            (newref, themis.codegen.ref(update_func), themis.codegen.ref(extra_args)))
    return FloatWrapper(newref)


def push_boolean(update_func, extra_args) -> themis.channel.BooleanOutput:
    newref = "pushb%d" % themis.codegen.next_uid()
    themis.codegen.add_code("def %s(bv):\n\t%s(bv, *%s)" %
                            (newref, themis.codegen.ref(update_func), themis.codegen.ref(extra_args)))
    return BooleanWrapper(newref)
