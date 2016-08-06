import themis.codegen
import enum
import themis.channel


def poll_float(event: themis.channel.EventInput, poll_func, args, default_value) -> themis.channel.FloatInput:
    c_out, c_in = themis.channel.float_cell(default_value)
    poll_ref = themis.codegen.ref(poll_func)
    arg_ref = themis.codegen.ref(args)

    @themis.channel.event.event_build
    def poll(ref: str):
        yield "%s(%s(*%s))" % (c_out.get_float_ref(), poll_ref, arg_ref)

    event.send(poll)
    return c_in


def poll_boolean(event: themis.channel.EventInput, poll_func, args, default_value) -> themis.channel.BooleanInput:
    c_out, c_in = themis.channel.boolean_cell(default_value)
    poll_ref = themis.codegen.ref(poll_func)
    arg_ref = themis.codegen.ref(args)

    @themis.channel.event.event_build
    def poll(ref: str):
        yield "%s(%s(*%s))" % (c_out.get_boolean_ref(), poll_ref, arg_ref)

    event.send(poll)
    return c_in


def poll_discrete(event: themis.channel.EventInput, poll_func, args, default_value: str,
                  discrete_type: themis.channel.Discrete) -> themis.channel.DiscreteInput:
    c_out, c_in = themis.channel.discrete_cell(default_value, discrete_type)
    poll_ref = themis.codegen.ref(poll_func)
    arg_ref = themis.codegen.ref(args)

    @themis.channel.event.event_build
    def poll(ref: str):
        yield "%s(%s(*%s))" % (c_out.get_discrete_ref(), poll_ref, arg_ref)

    event.send(poll)
    return c_in


def push_float(update_func, extra_args) -> themis.channel.FloatOutput:
    update_func = themis.codegen.ref(update_func)
    extra_args = themis.codegen.ref(extra_args)

    @themis.channel.float.float_build
    def push(ref: str):
        yield "%s(value, *%s)" % (update_func, extra_args)

    return push


def push_boolean(update_func, extra_args) -> themis.channel.BooleanOutput:
    update_func = themis.codegen.ref(update_func)
    extra_args = themis.codegen.ref(extra_args)

    @themis.channel.boolean.boolean_build
    def push(ref: str):
        yield "%s(value, *%s)" % (update_func, extra_args)

    return push
