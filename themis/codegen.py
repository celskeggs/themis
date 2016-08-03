import typing
import themis.codegen_inner

import themis.channel

NativeEventOutputType = typing.Callable[[], None]


class Context(themis.codegen_inner.InternalContext):
    def __init__(self):
        super().__init__()
        # init (super's register_init) is setting up machinery; begin is making it run.
        self._begin_execution = themis.channel.Event()

    def register_begin_exec(self, target: NativeEventOutputType) -> None:
        self.register_begin(self.event_exec(target))

    def register_begin(self, target: themis.channel.EventOutput) -> None:
        self._begin_execution.send(target)

    def event_exec(self, target: NativeEventOutputType) -> themis.channel.EventOutput:
        return ExecEventOutput(self.generate(target))

    def event_for_registrar(self, registrar: typing.Callable[[NativeEventOutputType], None]):
        return ExecEventInput(self, self.generate(registrar))

    def sample_derive_float(self, output: themis.channel.FloatOutput, target: typing.Callable[..., float],
                            args: typing.Sequence) -> themis.channel.EventOutput:
        return ExecEventOutput(self.lambda_exec("lambda update, pull, args: lambda: update(pull(*args))",
                                                output.generate_exec_float(self), target, args))

    def sample_derive_bool(self, output: themis.channel.BooleanOutput, target: typing.Callable[..., bool],
                            args: typing.Sequence) -> themis.channel.EventOutput:
        return ExecEventOutput(self.lambda_exec("lambda update, pull, args: lambda: update(pull(*args))",
                                                output.generate_exec_bool(self), target, args))

    def poll_derive_float(self, event: themis.channel.EventInput, target: typing.Callable[..., float],
                          args: typing.Sequence) -> themis.channel.FloatInput:
        cell = themis.channel.Float()
        update = self.sample_derive_float(cell, target, args)
        self.register_begin(update)
        event.send(update)
        return cell

    def poll_derive_bool(self, event: themis.channel.EventInput, target: typing.Callable[..., bool],
                          args: typing.Sequence) -> themis.channel.FloatInput:
        cell = themis.channel.Boolean()
        update = self.sample_derive_bool(cell, target, args)
        self.register_begin(update)
        event.send(update)
        return cell


class ExecEventOutput(themis.channel.EventOutput):
    def __init__(self, target: themis.codegen_inner.Generator):
        self._target = target

    def generate_exec_event(self, context: themis.codegen_inner.InternalContext) -> themis.codegen_inner.Generator:
        return self._target


class ExecEventInput(themis.channel.EventInput):
    def __init__(self, context, registrar: themis.codegen_inner.Generator):
        self._context = context
        self._registrar = registrar

    def send(self, target: themis.channel.EventOutput):
        self._context.register_init(
            self._context.lambda_exec("lambda registrar, callback: lambda: registrar(callback)", self._registrar,
                                      target.generate_exec_event(self._context)))
