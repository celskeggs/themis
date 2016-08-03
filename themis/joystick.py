import abc


class Joystick(abc.ABC):
    def deadzone(self, zone):
        return DeadzoneJoystick(self, zone)

    @abc.abstractmethod
    def axis(self, axis_num):  # 1-indexed
        pass

    @abc.abstractmethod
    def button(self, button_num):  # 1-indexed
        pass


class DeadzoneJoystick(Joystick):
    def __init__(self, base_joystick, zone):
        self._joy = base_joystick
        self._zone = zone

    def axis(self, axis_num):
        return self._joy.axis(axis_num).deadzone(self._zone)

    def button(self, button_num):
        return self._joy.button(button_num)
