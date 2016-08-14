import typing
import binascii

import themis.cbuild
import themis.auto
import themis.channel
import themis.codegen
import themis.codehelpers
import themis.joystick
import themis.pwm
import themis.timers

Mode = themis.channel.Discrete("DISABLED AUTONOMOUS TELEOP TESTING")

JOYSTICK_NUM = 6
AXIS_NUM = 12
MAX_BUTTON_NUM = 32
PWM_NUM = 20
PCM_NUM = 63
SOLENOID_NUM = 8
GPIO_NUM = 26
INTERRUPT_NUM = 8


class RoboRIO:
    def __init__(self):  # we have the required accessors mimic the actual route to a device. good idea? not sure.
        themis.codegen.add_init_call("ds_init", themis.codegen.InitPhase.PHASE_PREINIT_IO)
        self.driver_station = DriverStation()
        self.can = CAN()
        self.pwm = PWM()
        self.gpio = GPIO()

    def get_mode(self) -> themis.channel.DiscreteInput:
        return self.driver_station.get_mode()

    def is_mode(self, mode: Mode) -> themis.channel.BooleanInput:
        return self.get_mode().is_value(mode)

    def run_during_auto(self, autonomous: themis.auto.AutonomousType):
        should_run = self.is_mode(Mode.AUTONOMOUS)
        themis.auto.run_autonomous_while(should_run, autonomous)


# TODO: use appropriate exceptions for argument ranges instead of assertions


class GPIO:
    UNASSIGNED = 0
    INPUT = 1
    OUTPUT = 2

    def __init__(self):
        self._gpio_assignments = [GPIO.UNASSIGNED] * GPIO_NUM
        self._next_interrupt = 0
        self._poll_event = themis.timers.ticker(millis=20)

    def _alloc_interrupt(self) -> int:
        if self._next_interrupt >= INTERRUPT_NUM:
            raise Exception("Too many interrupts - can only allocate %d GPIO inputs with interrupts" % INTERRUPT_NUM)
        last = self._next_interrupt
        self._next_interrupt += 1
        return last

    def input(self, gpio_pin, interrupt=False) -> themis.channel.BooleanInput:
        assert self._gpio_assignments[gpio_pin] == GPIO.UNASSIGNED
        self._gpio_assignments[gpio_pin] = GPIO.INPUT
        if interrupt:
            interrupt_id = self._alloc_interrupt()
            themis.codegen.add_init_call("gpio_init_input_interrupt",
                                         themis.codegen.InitPhase.PHASE_INIT_IO, gpio_pin, interrupt_id)
            update_out, update_in = themis.channel.event_cell()
            themis.codegen.add_init_call("gpio_start_interrupt", themis.codegen.InitPhase.PHASE_BEGIN,
                                         gpio_pin, interrupt_id, update_out)
            return themis.codehelpers.poll_boolean(update_in, "gpio_poll_input", (gpio_pin,), False)
        else:
            themis.codegen.add_init_call("gpio_init_input_poll",
                                         themis.codegen.InitPhase.PHASE_INIT_IO, gpio_pin)
            return themis.codehelpers.poll_boolean(self._poll_event, "gpio_poll_input", (gpio_pin,), False)


class PWM:
    def __init__(self):
        pass

    def _frequency_to_squelch(self, freq: float) -> int:
        assert freq > 0
        if freq >= 133:
            return 0  # no squelching: 198 Hz
        elif freq >= 67:
            return 1  # half squelching: 99 Hz
        else:
            return 3  # full squelching: 49.5 Hz

    def talon_sr(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.TALON_SR)

    def jaguar(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.JAGUAR)

    def victor_old(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.VICTOR_OLD)

    def servo(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.SERVO, latch_zero=True)

    def victor_sp(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.VICTOR_SP)

    def spark(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.SPARK)

    def sd540(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.SD540)

    def talon_srx(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.TALON_SRX)

    def pwm_controller(self, pwm_id: int, specs: themis.pwm.SpeedControlSpecs,
                       latch_zero: bool = False) -> themis.channel.FloatOutput:
        return themis.pwm.filter_to(specs, self.pwm_raw(pwm_id, specs.frequency_hz, latch_zero=latch_zero))

    def pwm_raw(self, pwm_id: int, frequency: float, latch_zero: bool = False) -> themis.channel.FloatOutput:
        assert 0 <= pwm_id < PWM_NUM
        squelch = self._frequency_to_squelch(frequency)
        themis.codegen.add_init_call("pwm_init", themis.codegen.InitPhase.PHASE_INIT_IO, pwm_id, squelch, latch_zero)
        return themis.codehelpers.push_float("pwm_update", extra_args=(pwm_id,))


class CAN:  # TODO: implement!
    def __init__(self):
        # TODO: support multiple PCMs
        self.pcm = PCM(0)


class PCM:
    def __init__(self, pcm_id):
        assert 0 <= pcm_id < PCM_NUM
        self._id = pcm_id

    def solenoid(self, solenoid_id):
        assert 0 <= solenoid_id < SOLENOID_NUM
        themis.codegen.add_init_call("solenoid_init", themis.codegen.InitPhase.PHASE_INIT_IO, self._id,
                                     solenoid_id)
        return themis.codehelpers.push_boolean("solenoid_update", extra_args=(self._id, solenoid_id))


class DriverStation:
    def __init__(self):
        update_out, self._update = themis.channel.event_cell()
        themis.codegen.add_init_call("ds_begin", themis.codegen.InitPhase.PHASE_BEGIN, update_out)
        self.joysticks = [Joystick(i, self._update) for i in range(JOYSTICK_NUM)]
        self._get_mode = None

    def get_mode(self) -> themis.channel.DiscreteInput:
        if self._get_mode is None:
            self._get_mode = themis.codehelpers.poll_discrete(self._update, "get_robot_mode", (), Mode.DISABLED, Mode)
        return self._get_mode

    def joystick(self, i):
        return self.joysticks[i - 1]


class Joystick(themis.joystick.Joystick):
    def __init__(self, i: int, event_update_joysticks):
        self._index = i
        self._update = event_update_joysticks
        self._axes = [None] * AXIS_NUM
        self._buttons = [None] * MAX_BUTTON_NUM

    def _make_axis(self, i) -> themis.channel.FloatInput:
        return themis.codehelpers.poll_float(self._update, "get_joystick_axis", (self._index, i), 0)

    def _make_button(self, i) -> themis.channel.BooleanInput:
        return themis.codehelpers.poll_boolean(self._update, "get_joystick_button", (self._index, i), False)

    def axis(self, axis_num) -> themis.channel.FloatInput:
        axis_num -= 1
        if self._axes[axis_num] is None:
            self._axes[axis_num] = self._make_axis(axis_num)
        return self._axes[axis_num]

    def button(self, button_num) -> themis.channel.BooleanInput:
        button_num -= 1
        if self._buttons[button_num] is None:
            self._buttons[button_num] = self._make_button(button_num)
        return self._buttons[button_num]


def deploy_roboRIO(team_number: int, code):
    print("=============================================")
    print("Would deploy code to", team_number)
    # TODO: don't output to this kind of fixed path
    with open("/tmp/output.elf", "wb") as fout:
        fout.write(code)
    print("/tmp/output.elf")
    print("=============================================")


GCC_PREFIX = "arm-frc-linux-gnueabi-"
# note: these flags are duplicated in themis-frc-hal/CMakeLists.txt
C_FLAGS = "-Wformat=2 -Wall -Wextra -Werror -pedantic -Wno-psabi -Wno-unused-parameter -fPIC -Os -g0 -rdynamic " \
          "-std=c11 -D_POSIX_C_SOURCE=199309L"


def compile_roboRIO(c_code):
    return themis.cbuild.build_program(c_code, "themis.h", "libthemis-frc.so", GCC_PREFIX, C_FLAGS, __name__)


def robot(team_number: int, robot_constructor: typing.Callable[[RoboRIO], None]):
    with themis.codegen.GenerationContext().enter():
        roboRIO = RoboRIO()
        robot_constructor(roboRIO)
        compiled_code = compile_roboRIO(themis.codegen.generate_code())
        deploy_roboRIO(team_number, compiled_code)
