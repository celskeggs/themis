import threading
import math
import themis.exec.runloop
import typing

MODE_DISABLED = 0
MODE_AUTONOMOUS = 1
MODE_TELEOP = 2
MODE_TESTING = 3

JOYSTICK_NUM = 6
AXIS_NUM = 12
MAX_BUTTON_NUM = 32
PWM_NUM = 20
PCM_NUM = 63
SOLENOID_NUM = 8
GPIO_NUM = 26
INTERRUPT_NUM = 8

stick_axes = [()] * JOYSTICK_NUM
stick_povs = [()] * JOYSTICK_NUM
stick_buttons = [0] * JOYSTICK_NUM
stick_button_counts = [0] * JOYSTICK_NUM

cffi_stub = None
robot_mode = MODE_DISABLED


def ds_begin(target: typing.Callable[[], None]) -> None:
    threading.Thread(target=ds_mainloop, args=(target,)).start()


def ds_calc_mode(word):
    enabled = (word & cffi_stub.FRCNetworkCommunicationsLibrary.HAL_ENABLED) != 0
    autonomous = (word & cffi_stub.FRCNetworkCommunicationsLibrary.HAL_AUTONOMOUS) != 0
    test = (word & cffi_stub.FRCNetworkCommunicationsLibrary.HAL_TEST) != 0
    eStop = (word & cffi_stub.FRCNetworkCommunicationsLibrary.HAL_ESTOP) != 0
    dsAttached = (word & cffi_stub.FRCNetworkCommunicationsLibrary.HAL_DS_ATTACHED) != 0
    # TODO: does including eStop here cause any issues?
    if not enabled or not dsAttached or eStop:
        return MODE_DISABLED
    elif test:
        return MODE_TESTING
    elif autonomous:
        return MODE_AUTONOMOUS
    else:
        return MODE_TELEOP


class NotificationFlag:
    def __init__(self, default: bool):
        self._value = default
        self._lock = threading.Lock()

    def take(self) -> bool:
        with self._lock:
            if self._value:
                self._value = False
                return True
            return False

    def set(self) -> None:
        with self._lock:
            self._value = True


def ds_mainloop(target: typing.Callable[[], None]):
    global ds_ready, robot_mode
    data_mutex = cffi_stub.HALUtil.initializeMutexNormal()
    data_semaphor = cffi_stub.HALUtil.initializeMultiWait()
    cffi_stub.FRCNetworkCommunicationsLibrary.setNewDataSem(data_semaphor)

    ds_ready = NotificationFlag(True)
    def dispatch():
        ds_ready.set()
        target()

    while True:
        cffi_stub.HALUtil.takeMultiWait(data_semaphor, data_mutex)

        word = cffi_stub.FRCNetworkCommunicationsLibrary.NativeHALGetControlWord()
        onFMS = (word & cffi_stub.FRCNetworkCommunicationsLibrary.HAL_FMS_ATTACHED) != 0
        newmode = ds_calc_mode(word)
        if newmode != robot_mode:
            robot_mode = newmode

        if robot_mode == MODE_AUTONOMOUS:
            cffi_stub.FRCNetworkCommunicationsLibrary.FRCNetworkCommunicationObserveUserProgramAutonomous()
        elif robot_mode == MODE_TELEOP:
            cffi_stub.FRCNetworkCommunicationsLibrary.FRCNetworkCommunicationObserveUserProgramTeleop()
        elif robot_mode == MODE_TESTING:
            cffi_stub.FRCNetworkCommunicationsLibrary.FRCNetworkCommunicationObserveUserProgramTest()
        else:  # disabled
            cffi_stub.FRCNetworkCommunicationsLibrary.FRCNetworkCommunicationObserveUserProgramDisabled()

        for stick in range(JOYSTICK_NUM):
            stick_axes[stick] = list(cffi_stub.FRCNetworkCommunicationsLibrary.HALGetJoystickAxes(stick))
            stick_povs[stick] = list(cffi_stub.FRCNetworkCommunicationsLibrary.HALGetJoystickPOVs(stick))
            count_buffer = cffi_stub.allocate_byte_buffer(1)
            stick_buttons[stick] = cffi_stub.FRCNetworkCommunicationsLibrary.HALGetJoystickButtons(stick, count_buffer)
            stick_button_counts[stick] = count_buffer.get(0)

        if ds_ready.take():
            themis.exec.runloop.queue_event(dispatch)


def get_robot_mode() -> int:
    return robot_mode


def get_joystick_axis(joy_i: int, axis: int) -> float:
    assert 0 <= joy_i < JOYSTICK_NUM
    assert 0 <= axis < AXIS_NUM
    joy = stick_axes[joy_i]
    if axis >= len(joy):
        return 0.0
    raw_int = joy[axis]
    if raw_int < 0:
        return raw_int / 128.0
    else:
        return raw_int / 127.0


def get_joystick_button(joy_i: int, btn: int) -> bool:
    assert 0 <= joy_i < JOYSTICK_NUM
    assert 0 <= btn < MAX_BUTTON_NUM
    joy, count = stick_buttons[joy_i], stick_button_counts[joy_i]
    if btn >= count:
        return False
    return (joy & (1 << btn)) != 0


def pwm_frequency_to_squelch(frequency: float) -> int:
    assert frequency > 0
    if frequency >= 133:
        return 0  # no squelching: 198 Hz
    elif frequency >= 67:
        return 1  # half squelching: 99 Hz
    else:
        return 3  # full squelching: 49.5 Hz


pwms = [None] * PWM_NUM
PWM_GEN_CENTER = 1.5
PWM_CLOCK_KHZ = 40000.0
PWM_STEPS = 1000
PWM_SHIFT = None
PWM_MULTIPLIER = None


def pwm_init_config() -> None:
    global PWM_MULTIPLIER, PWM_SHIFT
    PWM_MULTIPLIER = PWM_CLOCK_KHZ / cffi_stub.DIOJNI.getLoopTiming()
    PWM_SHIFT = PWM_STEPS - 1 - PWM_GEN_CENTER * PWM_MULTIPLIER


def pwm_init(pwm_id: int, squelch: int, latch_pwm_zero: bool) -> None:
    assert pwms[pwm_id] is None
    port = cffi_stub.DIOJNI.initializeDigitalPort(cffi_stub.JNIWrapper.getPort(pwm_id))
    assert cffi_stub.PWMJNI.allocatePWMChannel(port), "PWM already allocated!"
    cffi_stub.PWMJNI.setPWM(port, 0)
    cffi_stub.PWMJNI.setPWMPeriodScale(port, squelch)
    if latch_pwm_zero:  # TODO: find out why we skip this for servos
        cffi_stub.PWMJNI.latchPWMZero(port)
    pwms[pwm_id] = port


def pwm_update(millis: float, pwm_id: int) -> None:
    if math.isnan(millis):
        cffi_stub.PWMJNI.setPWM(pwm_id, 0)
    else:
        scaled_value = int(millis * PWM_MULTIPLIER + PWM_SHIFT)
        cffi_stub.PWMJNI.setPWM(pwm_id, scaled_value)


solenoids = [[None] * SOLENOID_NUM for i in range(PCM_NUM)]


def solenoid_init(pcm_id: int, solenoid_id: int) -> None:
    assert solenoids[pcm_id][solenoid_id] is None
    solenoids[pcm_id][solenoid_id] = cffi_stub.SolenoidJNI.initializeSolenoidPort(
        cffi_stub.SolenoidJNI.getPortWithModule(pcm_id, solenoid_id))


def solenoid_update(on: bool, pcm_id: int, solenoid_id: int) -> None:
    port = solenoids[pcm_id][solenoid_id]
    assert port is not None
    cffi_stub.SolenoidJNI.setSolenoid(port, on)


GPIOS = [None] * GPIO_NUM
INTERRUPTS = [None] * INTERRUPT_NUM


def gpio_init_input_poll(gpio_pin: int) -> None:
    assert GPIOS[gpio_pin] is None
    GPIOS[gpio_pin] = cffi_stub.DIOJNI.initializeDigitalPort(cffi_stub.JNIWrapper.getPort(gpio_pin))
    cffi_stub.DIOJNI.allocateDIO(gpio_pin, True)  # True: as input


def gpio_poll_input(gpio_pin: int) -> bool:
    port = GPIOS[gpio_pin]
    assert port is not None
    return cffi_stub.DIOJNI.getDIO(port)


def gpio_init_input_interrupt(gpio_pin: int, interrupt_id: int) -> None:
    assert INTERRUPTS[interrupt_id] is None
    gpio_init_input_poll(gpio_pin)
    interrupt_port = cffi_stub.InterruptJNI.initializeInterrupts(interrupt_id, True)  # True: synchronous
    cffi_stub.InterruptJNI.requestInterrupts(interrupt_port, 0, gpio_pin, False)  # False: digital
    cffi_stub.InterruptJNI.setInterruptUpSourceEdge(interrupt_port, True, True)  # Trues: both rising and falling edge
    INTERRUPTS[interrupt_id] = interrupt_port


def gpio_start_interrupt(gpio_pin: int, interrupt_id: int, callback: typing.Callable[[bool], None]) -> None:
    interrupt_port = INTERRUPTS[interrupt_id]
    assert interrupt_port is not None
    gpio_port = GPIOS[gpio_pin]
    assert gpio_port is not None
    threading.Thread(target=gpio_interrupt_handler_thread, args=(gpio_port, interrupt_port, callback)).start()


def gpio_interrupt_handler_thread(gpio_port: int, interrupt_port: int, callback: typing.Callable[[bool], None]) -> None:
    last_value = None
    while True:
        # TODO: optimize based on timing out or not
        # False: don't ignore previous. 10.0: time out in 10 seconds. Why is this here? 10 seconds is pretty arbitrary.
        timed_out = cffi_stub.InterruptJNI.waitForInterrupt(interrupt_port, 10.0, False) == 0
        value = cffi_stub.DIOJNI.getDIO(gpio_port)
        if value != last_value:
            last_value = value
            themis.exec.runloop.queue_event(callback, value)
