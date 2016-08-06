import typing

import themis.channel.event
import themis.codegen
import themis.util

__all__ = ["BooleanOutput", "BooleanInput", "boolean_cell", "always_boolean"]


class BooleanOutput:
    def __init__(self, reference: str):
        assert isinstance(reference, str)
        self._ref = reference

    def get_boolean_ref(self) -> str:
        return self._ref

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    @property
    @themis.util.memoize_field
    def set_true(self) -> "themis.channel.event.EventOutput":
        @themis.channel.event.event_build
        def event_set_true(ref: str):
            yield "%s(True)" % self.get_boolean_ref()

        return event_set_true

    @property
    @themis.util.memoize_field
    def set_false(self) -> "themis.channel.event.EventOutput":
        @themis.channel.event.event_build
        def event_set_false(ref: str):
            yield "%s(False)" % self.get_boolean_ref()

        return event_set_false


class BooleanInput:
    def __init__(self, targets: list):
        assert isinstance(targets, list)
        self._targets = targets

    def send(self, output: BooleanOutput) -> None:
        assert isinstance(output, BooleanOutput)
        # TODO: default value?
        self._targets.append(output.get_boolean_ref())

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    @themis.util.memoize_field
    def _press_and_release(self) -> "typing.Tuple[themis.channel.event.EventInput, themis.channel.event.EventInput]":
        (press_out, press_in) = themis.channel.event.event_cell()
        (release_out, release_in) = themis.channel.event.event_cell()
        last_value = themis.codegen.add_variable(False)  # TODO: DEFAULT VALUES

        @boolean_build
        def check(ref: str):
            yield "globals %s" % last_value
            yield "if value == %s: return" % last_value
            yield "%s = value" % last_value
            yield "if value:"
            yield "\t%s()" % press_out.get_event_ref()
            yield "else:"
            yield "\t%s()" % release_out.get_event_ref()

        self.send(check)
        return press_in, release_in

    @property
    def press(self) -> "themis.channel.event.EventInput":
        return self._press_and_release()[0]

    @property
    def release(self) -> "themis.channel.event.EventInput":
        return self._press_and_release()[1]

    def choose_float(self, when_false: "themis.channel.float.FloatInput", when_true: "themis.channel.float.FloatInput") \
            -> "themis.channel.float.FloatInput":
        cell_out, cell_in = themis.channel.float.float_cell()

        # TODO: DEFAULT VALUES
        condition = themis.codegen.add_variable(False)
        when_true = themis.codegen.add_variable(0)
        when_false = themis.codegen.add_variable(0)

        @boolean_build
        def update_cond(ref: str):
            yield "globals %s, %s, %s" % (condition, when_true, when_false)
            yield "%s = value" % condition
            yield "%s(%s if %s else %s)" % (cell_out, when_true, condition, when_false)

        @themis.channel.float.float_build
        def update_true(ref: str):
            yield "globals %s, %s, %s" % (condition, when_true, when_false)
            yield "%s = value" % when_true
            yield "%s(%s if %s else %s)" % (cell_out, when_true, condition, when_false)

        @themis.channel.float.float_build
        def update_false(ref: str):
            yield "globals %s, %s, %s" % (condition, when_true, when_false)
            yield "%s = value" % when_false
            yield "%s(%s if %s else %s)" % (cell_out, when_true, condition, when_false)

        self.send(update_cond)
        when_false.send(update_false)
        when_true.send(update_true)

        return cell_in

    def choose(self, when_false, when_true):
        if isinstance(when_false, (int, float)):
            when_false = themis.channel.float.always_float(when_false)
        if isinstance(when_true, (int, float)):
            when_true = themis.channel.float.always_float(when_true)
        if isinstance(when_false, themis.channel.float.FloatInput):
            if not isinstance(when_true, themis.channel.float.FloatInput):
                raise TypeError("Parameters have different types: %s versus %s" % (when_false, when_true))
            return self.choose_float(when_false, when_true)
        else:
            # TODO: implement for booleans and discretes
            raise TypeError("when_false is of an invalid type: %s" % type(when_false))


def boolean_build(body_gen) -> BooleanOutput:
    def gen(ref: str):
        yield "def %s(value) -> None:" % ref
        for line in body_gen(ref):
            yield "\t%s" % (line,)

    return BooleanOutput(themis.codegen.add_code_gen_ref(gen))


def boolean_cell(default_value) -> typing.Tuple[BooleanOutput, BooleanInput]:
    # TODO: use default_value
    targets = []

    @boolean_build
    def dispatch(ref: str):
        if targets:
            for target in targets:
                yield "%s(value)" % (target,)
        else:
            yield "pass"

    return dispatch, BooleanInput(targets)


def always_boolean(value):
    return boolean_cell(value)[1]
