import threading
import math
import themis.exec.runloop

JOYSTICK_NUM = 6
AXIS_NUM = 12
MAX_BUTTON_NUM = 32
PWM_NUM = 20

stick_axes = [()] * JOYSTICK_NUM
stick_povs = [()] * JOYSTICK_NUM
stick_buttons = [0] * JOYSTICK_NUM
stick_button_counts = [0] * JOYSTICK_NUM

cffi_stub = None
ds_ready_cond = threading.Lock()
ds_ready = True
ds_dispatch_event = None


def ds_begin():
    threading.Thread(target=ds_mainloop).start()


def ds_set_event(event):
    global ds_dispatch_event
    ds_dispatch_event = event


def ds_mainloop():
    global ds_ready
    data_mutex = cffi_stub.HALUtil.initializeMutexNormal()
    data_semaphor = cffi_stub.HALUtil.initializeMultiWait()
    cffi_stub.FRCNetworkCommunicationsLibrary.setNewDataSem(data_semaphor)
    while True:
        cffi_stub.HALUtil.takeMultiWait(data_semaphor, data_mutex)

        for stick in range(JOYSTICK_NUM):
            stick_axes[stick] = list(cffi_stub.FRCNetworkCommunicationsLibrary.HALGetJoystickAxes(stick))
            stick_povs[stick] = list(cffi_stub.FRCNetworkCommunicationsLibrary.HALGetJoystickPOVs(stick))
            count_buffer = cffi_stub.allocate_byte_buffer(1)
            stick_buttons[stick] = cffi_stub.FRCNetworkCommunicationsLibrary.HALGetJoystickButtons(stick, count_buffer)
            stick_button_counts[stick] = count_buffer.get(0)

        with ds_ready_cond:
            if ds_ready:
                themis.exec.runloop.queue_event(ds_dispatch)
                ds_ready = False


def ds_dispatch():
    global ds_ready
    with ds_ready_cond:
        ds_ready = True
    ds_dispatch_event()


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


def get_joystick_button(joy_i: int, btn: int) -> float:
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


def pwm_init_config():
    global PWM_MULTIPLIER, PWM_SHIFT
    PWM_MULTIPLIER = PWM_CLOCK_KHZ / cffi_stub.DIOJNI.getLoopTiming()
    PWM_SHIFT = PWM_STEPS - 1 - PWM_GEN_CENTER * PWM_MULTIPLIER


def pwm_init(pwm_id: int, squelch: int, latch_pwm_zero: float) -> None:
    assert pwms[pwm_id] is None
    port = cffi_stub.DIOJNI.initializeDigitalPort(cffi_stub.JNIWrapper.getPort(pwm_id))
    assert cffi_stub.PWMJNI.allocatePWMChannel(port), "PWM already allocated!"
    cffi_stub.PWMJNI.setPWM(port, 0)
    cffi_stub.PWMJNI.setPWMPeriodScale(port, squelch)
    if latch_pwm_zero:  # TODO: find out why we skip this for servos
        cffi_stub.PWMJNI.latchPWMZero(port)
    pwms[pwm_id] = port


def pwm_update(millis: float, pwm_id: int):
    if math.isnan(millis):
        cffi_stub.PWMJNI.setPWM(pwm_id, 0)
    else:
        scaled_value = int(millis * PWM_MULTIPLIER + PWM_SHIFT)
        cffi_stub.PWMJNI.setPWM(pwm_id, scaled_value)
