import typing
import themis.exec

import themis.channel.event
import themis.codegen
import themis.util
import themis.pygen

__all__ = ["BooleanOutput", "BooleanInput", "boolean_cell", "always_boolean"]


class BooleanOutput:
    def __init__(self, instant: themis.pygen.Instant):
        assert isinstance(instant, themis.pygen.Instant)
        self._instant = instant

    def get_ref(self) -> themis.pygen.Instant:
        return self._instant

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    def filter(self, filter_func, pre_args=(), post_args=()) -> "BooleanOutput":
        instant = themis.pygen.Instant(bool)
        instant.transform(filter_func, self.get_ref(), *pre_args, themis.pygen.Param, *post_args)
        return BooleanOutput(instant)

    @property
    @themis.util.memoize_field
    def set_true(self) -> "themis.channel.event.EventOutput":
        instant = themis.pygen.Instant(None)
        instant.invoke(self.get_ref(), True)
        return themis.channel.EventOutput(instant)

    @property
    @themis.util.memoize_field
    def set_false(self) -> "themis.channel.event.EventOutput":
        instant = themis.pygen.Instant(None)
        instant.invoke(self.get_ref(), True)
        return themis.channel.EventOutput(instant)


class BooleanInput:
    def __init__(self, instant: themis.pygen.Instant, default_value: bool):
        assert isinstance(instant, themis.pygen.Instant)
        assert isinstance(default_value, bool)
        self._instant = instant
        self._default_value = default_value
        # TODO: cache the current value in a shared way, rather than having each user of the current value track it separately.

    def send(self, output: BooleanOutput) -> None:
        assert isinstance(output, BooleanOutput)
        # TODO: default value?
        self._instant.invoke(output.get_ref(), themis.pygen.Param)

    def __bool__(self):
        raise TypeError("Cannot convert IO channels to bool")

    @themis.util.memoize_field
    def _press_and_release(self) -> "typing.Tuple[themis.channel.event.EventInput, themis.channel.event.EventInput]":
        become_true = themis.pygen.Instant(None)
        become_false = themis.pygen.Instant(None)

        last_value = themis.pygen.Box(self._default_value)

        on_update = themis.pygen.Instant(bool)
        self._instant.if_unequal(themis.pygen.Param, last_value, on_update, themis.pygen.Param)
        on_update.set(last_value, themis.pygen.Param)
        on_update.if_else(themis.pygen.Param, True, become_true, become_false)

        return themis.channel.event.EventInput(become_true), themis.channel.event.EventInput(become_false)

    @property
    def press(self) -> "themis.channel.event.EventInput":
        return self._press_and_release()[0]

    @property
    def release(self) -> "themis.channel.event.EventInput":
        return self._press_and_release()[1]

    def choose_float(self, when_false: "themis.channel.float.FloatInput", when_true: "themis.channel.float.FloatInput") \
            -> "themis.channel.float.FloatInput":
        # TODO: do default values without accessing private fields
        cell_out, cell_in = themis.channel.float.float_cell(when_true._default_value if self._default_value else
                                                            when_false._default_value)

        condition = themis.pygen.Box(self._default_value)
        var_true = themis.pygen.Box(when_true._default_value)
        var_false = themis.pygen.Box(when_false._default_value)

        self._instant.set(condition, themis.pygen.Param)
        self._instant.transform(themis.exec.filters.choose_float, cell_out.get_ref(), condition, var_true, var_false)

        when_true._instant.set(var_true, themis.pygen.Param)
        when_true._instant.transform(themis.exec.filters.choose_float, cell_out.get_ref(), condition, var_true,
                                     var_false)

        when_false._instant.set(var_false, themis.pygen.Param)
        when_false._instant.transform(themis.exec.filters.choose_float, cell_out.get_ref(), condition, var_true,
                                      var_false)

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

    @property
    @themis.util.memoize_field
    def inverted(self):
        instant = themis.pygen.Instant(bool)
        self._instant.transform(themis.exec.filters.invert, instant, themis.pygen.Param)
        return InvertedBooleanInput(instant, not self._default_value, base=self)

    def __and__(self, other):
        if isinstance(other, bool):
            if other:
                return self
            else:
                return always_boolean(False)
        elif isinstance(other, BooleanInput):
            cell_out, cell_in = boolean_cell(self._default_value and other._default_value)

            value_self = themis.pygen.Box(self._default_value)
            value_other = themis.pygen.Box(other._default_value)

            for value, input in zip((value_self, value_other), (self, other)):
                input._instant.set(value, themis.pygen.Param)
                input._instant.transform(themis.exec.filters.and_bool, cell_out.get_ref(), value_self, value_other)
            return cell_in
        else:
            return NotImplemented

    def __rand__(self, other):
        if isinstance(other, bool):
            if other:
                return self
            else:
                return always_boolean(False)
        else:
            assert not isinstance(other, BooleanInput), "should have dispatched to __and__"
            return NotImplemented


class InvertedBooleanInput(BooleanInput):
    def __init__(self, instant: themis.pygen.Instant, default_value: bool, base: BooleanInput):
        super().__init__(instant, default_value)
        self._base = base

    @themis.util.memoize_field
    def _press_and_release(self) -> "typing.Tuple[themis.channel.event.EventInput, themis.channel.event.EventInput]":
        become_true, become_false = self._base._press_and_release()
        return become_false, become_true  # flip them!

    def inverted(self):
        return self._base


class BooleanIO:
    def __init__(self, output: BooleanOutput, input: BooleanInput):
        assert isinstance(output, BooleanOutput)
        assert isinstance(input, BooleanInput)
        self.output = output
        self.input = input

    def __iter__(self):  # TODO: get this to typecheck properly
        return iter((self.output, self.input))

    @property
    @themis.util.memoize_field
    def toggle(self) -> "themis.channel.event.EventOutput":
        last_value = themis.pygen.Box(self.input._default_value)
        self.input._instant.set(last_value, themis.pygen.Param)

        instant = themis.pygen.Instant(None)
        instant.transform(themis.exec.filters.invert, self.output.get_ref(), last_value)
        return themis.channel.event.EventOutput(instant)


# TODO: should we be doing deduplication in cells? probably.
def boolean_cell(default_value) -> BooleanIO:
    instant = themis.pygen.Instant(bool)
    return BooleanIO(BooleanOutput(instant), BooleanInput(instant, default_value))


def always_boolean(value):
    return boolean_cell(value).input
