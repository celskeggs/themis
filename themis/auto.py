import typing
import themis.timers
import themis.channel


# TODO: implement cancellation
class ActionSnapshot:
    def __init__(self, begin: themis.channel.EventInput, should_cancel: themis.channel.BooleanInput):
        self._cancel = should_cancel
        self._begin = begin

    def set(self, target, value):
        if isinstance(target, themis.channel.BooleanOutput):
            assert isinstance(value, bool)
            self._begin.send(target.set_true if value else target.set_false)
        elif isinstance(target, themis.channel.FloatOutput):
            assert isinstance(value, (int, float))
            self._begin.send(target.set_event(value))
        else:
            raise TypeError("Invalid set parameter: %s" % type(target))

    def after_ms(self, milliseconds: float) -> themis.channel.EventInput:
        # TODO: don't fire event if we've cancelled
        return themis.timers.after_ms(self._begin, milliseconds)

    def defer_ms(self, milliseconds: float) -> "ActionSnapshot":
        return ActionSnapshot(self.after_ms(milliseconds), self._cancel)

    def and_then(self, input: themis.channel.BooleanInput) -> themis.channel.EventInput:
        waiting_out, waiting_in = themis.channel.boolean_cell(False)
        end_out, end_in = themis.channel.event_cell()

        self.set(waiting_out, True)
        waiting_out.set_false.when(self._cancel.press)
        waiting_out.set_false.when(end_in)

        (waiting_in & input).press.send(end_out)  # TODO: a short delay, perhaps?
        return end_in

    def defer_until(self, input: themis.channel.BooleanInput) -> "ActionSnapshot":
        return ActionSnapshot(self.and_then(input), self._cancel)


class ActionState:
    def __init__(self, begin: themis.channel.EventInput, should_cancel: themis.channel.BooleanInput):
        self._cancel = should_cancel
        self.snapshot = ActionSnapshot(begin, should_cancel)

    def set(self, target, value) -> None:
        self.snapshot.set(target, value)

    def wait_ms(self, milliseconds: float) -> None:
        self.snapshot = self.snapshot.defer_ms(milliseconds)

    def wait_until(self, input: themis.channel.BooleanInput) -> None:
        self.snapshot = self.snapshot.defer_until(input)


AutonomousType = typing.Callable[[ActionState], None]


def run_autonomous_while(should_run: themis.channel.BooleanInput, autonomous: AutonomousType) -> None:
    should_cancel = should_run.inverted
    act = ActionState(should_run.press, should_cancel)
    autonomous(act)
