import typing
import themis.codegen

import themis.channel

NativeEventOutputType = typing.Callable[[], None]


def get_begin_calls() -> typing.List:
    return themis.codegen.get_context().get_prop_init(get_begin_calls, lambda: [])


def register_begin_call(target) -> None:
    get_begin_calls().append(themis.codegen.get_context().generate(target))


def event_exec(target: NativeEventOutputType) -> themis.channel.EventOutput:
    return themis.channel.ExecEventOutput(themis.codegen.get_context().generate(target))


def event_for_registrar(registrar: typing.Callable[[NativeEventOutputType], None]):
    return themis.channel.ExecEventInput(themis.codegen.get_context().generate(registrar))


def sample_derive_float(output: themis.channel.FloatOutput, target: typing.Callable[..., float],
                        args: typing.Sequence) -> themis.channel.EventOutput:
    return themis.channel.ExecEventOutput(themis.codegen.gen_lambda("lambda: update(pull(*args))",
                                                                    update=output.generate_exec_float(), pull=target,
                                                                    args=args))


def sample_derive_bool(output: themis.channel.BooleanOutput, target: typing.Callable[..., bool],
                       args: typing.Sequence) -> themis.channel.EventOutput:
    return themis.channel.ExecEventOutput(themis.codegen.gen_lambda("lambda: update(pull(*args))",
                                                                    update=output.generate_exec_bool(), pull=target,
                                                                    args=args))


def poll_derive_float(event: themis.channel.EventInput, target: typing.Callable[..., float],
                      args: typing.Sequence) -> themis.channel.FloatInput:
    cell = themis.channel.Float()
    update = sample_derive_float(cell, target, args)
    register_begin_call(update.generate_exec_event())
    event.send(update)
    return cell


def poll_derive_bool(event: themis.channel.EventInput, target: typing.Callable[..., bool],
                     args: typing.Sequence) -> themis.channel.FloatInput:
    cell = themis.channel.Boolean()
    update = sample_derive_bool(cell, target, args)
    register_begin_call(update.generate_exec_event())
    event.send(update)
    return cell
