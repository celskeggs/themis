import typing
import themis.codehelpers
import themis.channel
import themis.codeinit
import themis.codegen
import themis.exec
import themis.pwm
import themis.joystick


class RoboRIO:
    def __init__(self):
        self.driver_station = DriverStation()
        themis.codeinit.add_init_call(themis.codegen.ref(themis.exec.frc.pwm_init_config),
                                      themis.codeinit.Phase.PHASE_INIT_IO)

    def talon_sr(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.TALON_SR)

    def jaguar(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.JAGUAR)

    def victor_old(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.VICTOR_OLD)

    def servo(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.SERVO, latch_pwm_zero=True)

    def victor_sp(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.VICTOR_SP)

    def spark(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.SPARK)

    def sd540(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.SD540)

    def talon_srx(self, pwm_id: int) -> themis.channel.FloatOutput:
        return self.pwm_controller(pwm_id, themis.pwm.TALON_SRX)

    def pwm_controller(self, pwm_id: int, specs: themis.pwm.SpeedControlSpecs,
                       latch_pwm_zero: bool = False) -> themis.channel.FloatOutput:
        return themis.pwm.filter_to(specs, self.pwm_raw(pwm_id, specs.frequency_hz, latch_pwm_zero=latch_pwm_zero))

    def pwm_raw(self, pwm_id: int, frequency: float, latch_pwm_zero: bool = False) -> themis.channel.FloatOutput:
        squelch = themis.exec.frc.pwm_frequency_to_squelch(frequency)
        themis.codeinit.add_init_call(themis.codegen.ref(themis.exec.frc.pwm_init), themis.codeinit.Phase.PHASE_INIT_IO,
                                      args=(pwm_id, squelch, latch_pwm_zero))
        return themis.codehelpers.push_float(themis.exec.frc.pwm_update, extra_args=(pwm_id,))


class DriverStation:
    def __init__(self):
        self._update = themis.channel.EventCell()
        themis.codeinit.add_init_call(themis.codegen.ref(themis.exec.frc.ds_begin), themis.codeinit.Phase.PHASE_BEGIN,
                                      args=(self._update,))
        self.joysticks = [Joystick(i, self._update) for i in range(themis.exec.frc.JOYSTICK_NUM)]

    def joystick(self, i):
        return self.joysticks[i - 1]


class Joystick(themis.joystick.Joystick):
    def __init__(self, i: int, event_update_joysticks):
        self._index = i
        self._update = event_update_joysticks
        self._axes = [self._make_axis(i) for i in range(themis.exec.frc.AXIS_NUM)]
        self._buttons = [self._make_button(i) for i in range(themis.exec.frc.MAX_BUTTON_NUM)]

    def _make_axis(self, i):
        return themis.codehelpers.poll_float(self._update, themis.exec.frc.get_joystick_axis, (self._index, i))

    def _make_button(self, i):
        return themis.codehelpers.poll_boolean(self._update, themis.exec.frc.get_joystick_button, (self._index, i))

    def axis(self, axis_num):
        return self._axes[axis_num - 1]

    def button(self, button_num):
        return self._buttons[button_num - 1]


def deploy_roboRIO(team_number: int, code):
    print("=============================================")
    print("Would deploy code to", team_number)
    print(code)
    print("=============================================")


def robot(team_number: int, robot_constructor: typing.Callable[[RoboRIO], None]):
    with themis.codegen.GenerationContext().enter():
        roboRIO = RoboRIO()
        robot_constructor(roboRIO)
        deploy_roboRIO(team_number, roboRIO.generate_code())
