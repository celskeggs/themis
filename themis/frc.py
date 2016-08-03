import typing
import themis.exec
import themis.joystick
import themis.codegen

class RoboRIO:
    def __init__(self, context: themis.codegen.Context):
        self._context = context
        self.driver_station = DriverStation(context)


class DriverStation:
    def __init__(self, context: themis.codegen.Context):
        self._context = context
        context.register_begin_exec(themis.exec.frc.ds_begin)
        self._update = context.event_for_registrar(themis.exec.frc.ds_dispatch_register)
        self.joysticks = [Joystick(context, i, self._update) for i in range(themis.exec.frc.JOYSTICK_NUM)]

    def joystick(self, i):
        return self.joysticks[i - 1]


class Joystick(themis.joystick.Joystick):
    def __init__(self, context: themis.codegen.Context, i: int, event_update_joysticks):
        self._context = context
        self._index = i
        self._update = event_update_joysticks
        self._axes = [self._make_axis(i) for i in range(themis.exec.frc.AXIS_NUM)]
        self._buttons = [self._make_button(i) for i in range(themis.exec.frc.MAX_BUTTON_NUM)]

    def _make_axis(self, i):
        return self._context.poll_derive_float(self._update, themis.exec.frc.get_joystick_axis, args=(self._index, i))

    def _make_button(self, i):
        return self._context.poll_derive_bool(self._update, themis.exec.frc.get_joystick_button, args=(self._index, i))

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
    context = themis.codegen.Context()
    roboRIO = RoboRIO(context)
    robot_constructor(roboRIO)
    deploy_roboRIO(team_number, roboRIO.generate_code())
