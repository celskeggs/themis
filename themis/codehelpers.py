import themis.channel
import themis.codegen
import themis.cgen


def poll_float(event: themis.channel.EventInput, poll_func, args, default_value: float) -> themis.channel.FloatInput:
    dispatch = themis.cgen.Instant(float)
    event.get_instant().transform(poll_func, dispatch, *args)
    return themis.channel.float.FloatInput(dispatch, default_value)


def poll_boolean(event: themis.channel.EventInput, poll_func, args, default_value: bool) -> themis.channel.BooleanInput:
    dispatch = themis.cgen.Instant(bool)
    event.get_instant().transform(poll_func, dispatch, *args)
    return themis.channel.boolean.BooleanInput(dispatch, default_value)


def poll_discrete(event: themis.channel.EventInput, poll_func, args, default_value: str,
                  discrete_type: themis.channel.Discrete) -> themis.channel.DiscreteInput:
    dispatch = themis.cgen.Instant(int)
    event.get_instant().transform(poll_func, dispatch, *args)
    return themis.channel.discrete.DiscreteInput(dispatch, default_value, discrete_type)


def push_float(update_func, extra_args) -> themis.channel.FloatOutput:
    instant = themis.cgen.Instant(float)
    instant.transform(update_func, None, themis.cgen.Param, *extra_args)
    return themis.channel.float.FloatOutput(instant)


def push_boolean(update_func, extra_args) -> themis.channel.BooleanOutput:
    instant = themis.cgen.Instant(bool)
    instant.transform(update_func, None, themis.cgen.Param, *extra_args)
    return themis.channel.boolean.BooleanOutput(instant)