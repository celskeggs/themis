import threading
import themis.exec.runloop

JOYSTICK_NUM = 6
AXIS_NUM = 12
MAX_BUTTON_NUM = 32

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
