import abc
import themis.channel.event
import themis.codegen

__all__ = ["BooleanOutput", "BooleanInput", "BooleanCell", "always_boolean"]


class BooleanOutput(abc.ABC):
    def __init__(self):
        super().__init__()
        self._set_true, self._set_false = None, None

    @abc.abstractmethod
    def get_reference(self) -> str:
        pass

    @abc.abstractmethod
    def send_default_value(self, value: bool):
        pass

    @property
    def set_true(self) -> "themis.channel.event.EventOutput":
        if self._set_true is None:
            import themis.codehelpers
            ref = "set_true_%s" % self.get_reference()
            themis.codegen.add_code("def %s():\n\t%s(True)" % (ref, self.get_reference()))
            self._set_true = themis.codehelpers.EventWrapper(ref)
        return self._set_true

    @property
    def set_false(self) -> "themis.channel.event.EventOutput":
        if self._set_false is None:
            import themis.codehelpers
            ref = "set_false_%s" % self.get_reference()
            themis.codegen.add_code("def %s():\n\t%s(False)" % (ref, self.get_reference()))
            self._set_false = themis.codehelpers.EventWrapper(ref)
        return self._set_false


class BooleanInput(abc.ABC):
    def __init__(self):
        super().__init__()
        self._press, self._release = None, None

    # TODO: more precise checking when sending to make sure that Floats and Booleans can't be intermixed.
    def send(self, output: BooleanOutput) -> None:
        output.send_default_value(self.default_value())
        self._send(output)

    @abc.abstractmethod
    def _send(self, output: BooleanOutput) -> None:
        pass

    @abc.abstractmethod
    def default_value(self) -> bool:
        pass

    def _gen_change_checker(self, press: bool) -> "themis.channel.event.EventInput":
        cell = themis.channel.event.EventCell()
        ref = "change%d" % themis.codegen.next_uid()
        themis.codegen.add_code(
            "last_%s = %s\ndef %s(bv):\n\tglobals last_%s\n\tif bv == last_%s: return\n\tlast_%s = bv\n\tif bv != %s: return\n\t%s()" %
            (ref, self.default_value(), ref, ref, ref, ref, press, cell))
        return cell

    @property
    def press(self) -> "themis.channel.event.EventInput":
        if self._press is None:
            self._press = self._gen_change_checker(press=True)
        return self._press

    @property
    def release(self) -> "themis.channel.event.EventInput":
        if self._release is None:
            self._release = self._gen_change_checker(press=False)
        return self._release

    # TODO: are these aliases useful?
    @property
    def become_true(self):
        return self.press

    @property
    def become_false(self):
        return self.release

    # TODO: failing __bool__

    def choose_float(self, when_false: "themis.channel.float.FloatInput", when_true: "themis.channel.float.FloatInput") \
            -> "themis.channel.float.FloatInput":
        import themis.codehelpers  # here to avoid issues with circular references
        out = themis.channel.float.FloatCell()
        out.send_default_value(when_true.default_value() if self.default_value() else when_false.default_value())
        ref = "ref%d" % themis.codegen.next_uid()
        for ctf, inp in zip("ctf", (self, when_true, when_false)):
            themis.codegen.add_code("v%s_%s = %s" % (ctf, ref, inp.default_value()))
            themis.codegen.add_code(
                "def m%s_%s(v):\n\tglobals vc_%s, vt_%s, vf_%s\n\tv%s_%s = fv\n\t%s(vt_%s if vc_%s else vf_%s)"
                % (ctf, ref, ref, ref, ref, ctf, ref, out.get_reference(), ref, ref, ref))
            if ctf == "c":
                inp.send(themis.codehelpers.BooleanWrapper("mc_%s" % (ref,)))
            else:
                inp.send(themis.codehelpers.FloatWrapper("m%s_%s" % (ctf, ref)))
        return out

    # TODO: don't duplicate code between choose_float and choose_boolean

    def choose_boolean(self, when_false: "BooleanInput", when_true: "BooleanInput") -> "BooleanInput":
        import themis.codehelpers  # here to avoid issues with circular references
        out = BooleanCell()
        out.send_default_value(when_true.default_value() if self.default_value() else when_false.default_value())
        ref = "ref%d" % themis.codegen.next_uid()
        for ctf, inp in zip("ctf", (self, when_true, when_false)):
            themis.codegen.add_code("v%s_%s = %s" % (ctf, ref, inp.default_value()))
            themis.codegen.add_code(
                "def m%s_%s(v):\n\tglobals vc_%s, vt_%s, vf_%s\n\tv%s_%s = fv\n\t%s(vt_%s if vc_%s else vf_%s)"
                % (ctf, ref, ref, ref, ref, ctf, ref, out.get_reference(), ref, ref, ref))
            inp.send(themis.codehelpers.BooleanWrapper("m%s_%s" % (ctf, ref)))
        return out

    def choose(self, when_false, when_true):
        if isinstance(when_false, (int, float)):
            when_false = themis.channel.float.always_float(when_false)
        if isinstance(when_true, (int, float)):
            when_true = themis.channel.float.always_float(when_true)
        if isinstance(when_false, themis.channel.float.FloatInput):
            if not isinstance(when_true, themis.channel.float.FloatInput):
                raise TypeError("Parameters have different types: %s versus %s" % (when_false, when_true))
            assert not isinstance(when_false, BooleanInput) and not isinstance(when_true, BooleanInput)
            return self.choose_float(when_false, when_true)
        elif isinstance(when_false, BooleanInput):
            if not isinstance(when_true, BooleanInput):
                raise TypeError("Parameters have different types: %s versus %s" % (when_false, when_true))
            assert not isinstance(when_false, themis.channel.float.FloatInput)
            assert not isinstance(when_true, themis.channel.float.FloatInput)
            return self.choose_boolean(when_false, when_true)
        else:
            raise TypeError("when_false is of an invalid type: %s" % type(when_false))


# TODO: deduplicate identical sets here and in FloatCell?

class BooleanCell(themis.codegen.RefGenerator, BooleanInput, BooleanOutput):
    def __init__(self, value=False):
        super().__init__()
        self._default_value = value
        self._default_value_queried = False
        self._targets = []
        self._toggle = None

    def default_value(self):
        self._default_value_queried = True
        return self._default_value

    def _send(self, target: BooleanOutput):
        self._targets.append(target)

    def send_default_value(self, value: bool):
        if value != self._default_value:
            assert not self._default_value_queried, "Default value changed after usage!"

    def generate_ref_code(self, ref):
        yield "value_%s = %s" % (ref, self._default_value)
        yield "def %s(bv: bool) -> None:" % ref
        yield "\tglobals value_%s" % ref
        yield "\tif bv == value_%s: return" % ref
        yield "\tvalue_%s = bv" % ref
        for target in self._targets:
            yield "\t%s(bv)" % target.get_reference()

    @property
    def toggle(self) -> "themis.channel.event.EventOutput":
        if self._toggle is None:
            import themis.codehelpers  # here to avoid issues with circular references
            ref = self.get_reference()
            toggle_ref = "toggle_%s" % ref
            themis.codegen.add_code("def %s():\n\t%s(not value_%s)" % (toggle_ref, ref, ref))
            self._toggle = themis.codehelpers.EventWrapper(toggle_ref)
        return self._toggle


def always_boolean(value):
    return FixedBooleanInput(value)


class FixedBooleanInput(BooleanInput):
    def __init__(self, value: bool):
        super().__init__()
        self._value = value

    def default_value(self):
        return self._value

    def send(self, output: BooleanOutput):
        super(FixedBooleanInput, self).send(output)
        # no changes, so we don't bother doing anything with it!
