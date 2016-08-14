#include <pthread.h>
#include "themis.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <HAL/HAL.hpp>

enum frc_mode {
    MODE_DISABLED = 0,
    MODE_AUTONOMOUS = 1,
    MODE_TELEOP = 2,
    MODE_TESTING = 3
};

#define JOYSTICK_NUM 6
#define AXIS_NUM 12
#define MAX_BUTTON_NUM 32
#define PWM_NUM 20
#define PCM_NUM 63
#define SOLENOID_NUM 8
#define GPIO_NUM 26
#define INTERRUPT_NUM 8

static enum frc_mode robot_mode = MODE_DISABLED;
static volatile bool ds_ready = true;
static callback ds_dispatch_target = NULL;
static pthread_t ds_main_thread;
static bool ds_run = true; // TODO: eliminate or use this

static struct HALJoystickAxes stick_axes[JOYSTICK_NUM];
static struct HALJoystickPOVs stick_povs[JOYSTICK_NUM];
static struct HALJoystickButtons stick_buttons[JOYSTICK_NUM];

static void *ds_mainloop(void *);

static void pwm_init_config(void);

void ds_init(void) { // TODO: make sure this is used
    HALInitialize(0);
    pwm_init_config();
}

void ds_begin(callback target) {
    assert(ds_dispatch_target == NULL && target != NULL);
    ds_dispatch_target = target;
    pthread_create(&ds_main_thread, NULL, ds_mainloop, NULL);
}

// TODO: also do something about warnings?
#define HAL_CHECK(status, info) if (status < 0) { hal_panic(info, status); }

static void hal_panic(const char *info, int32_t status) {
    fprintf(stderr, "errno %d: %s\n", status, getHALErrorMessage(status));
    panic(info);
}

static void ds_dispatch(void) {
    ds_ready = true;
    ds_dispatch_target();
}

static enum frc_mode ds_calc_mode(HALControlWord word) {
    // TODO: use word.fmsAttached
    if (!word.enabled || !word.dsAttached || !word.eStop) {
        return MODE_DISABLED;
    } else if (word.test) {
        return MODE_TESTING;
    } else if (word.autonomous) {
        return MODE_AUTONOMOUS;
    } else {
        return MODE_TELEOP;
    }
}

static void *ds_mainloop(void *param) {
    // TODO: check results of functions

    MUTEX_ID data_mutex = initializeMutexNormal();
    MULTIWAIT_ID data_semaphor = initializeMultiWait();
    HALSetNewDataSem(data_semaphor);

    HALNetworkCommunicationObserveUserProgramStarting(); // TODO: could we do this at a later point in time?

    while (ds_run) {
        takeMultiWait(data_semaphor, data_mutex);

        HALControlWord word;
        HALGetControlWord(&word); // the official code ignores the return value. apparently it's okay.
        robot_mode = ds_calc_mode(word);

        switch (robot_mode) {
            case MODE_AUTONOMOUS:
                HALNetworkCommunicationObserveUserProgramAutonomous();
                break;
            case MODE_TELEOP:
                HALNetworkCommunicationObserveUserProgramTeleop();
                break;
            case MODE_TESTING:
                HALNetworkCommunicationObserveUserProgramTest();
                break;
            default: // disabled
                HALNetworkCommunicationObserveUserProgramDisabled();
                break;
        }

        for (uint8_t stick = 0; stick < JOYSTICK_NUM; stick++) {
            // again, the return values here are ignored in the official code. huh.
            HALGetJoystickAxes(stick, &stick_axes[stick]);
            HALGetJoystickPOVs(stick, &stick_povs[stick]);
            HALGetJoystickButtons(stick, &stick_buttons[stick]);
        }

        // atomically set to false and, if it were true, go on to queue the event
        if (__sync_fetch_and_and(&ds_ready, 0)) {
            queue_event(ds_dispatch);
        }
    }
    return NULL;
}

int get_robot_mode() {
    return robot_mode;
}

double get_joystick_axis(int joy_i, int axis) {
    assert(0 <= joy_i && joy_i < JOYSTICK_NUM);
    assert(0 <= axis && axis < AXIS_NUM);
    struct HALJoystickAxes axes = stick_axes[joy_i];
    if (axis >= axes.count) {
        return 0.0;
    } else {
        int16_t raw = axes.axes[axis];
        return raw < 0 ? raw / 128.0 : raw / 127.0;
    }
}

bool get_joystick_button(int joy_i, int btn) {
    assert(0 <= joy_i && joy_i < JOYSTICK_NUM);
    assert(0 <= btn && btn < MAX_BUTTON_NUM);
    struct HALJoystickButtons buttons = stick_buttons[joy_i];
    if (btn >= buttons.count) {
        return false;
    } else {
        return (buttons.buttons & (1 << btn)) != 0;
    }
}

#define PWM_GEN_CENTER 1.5
#define PWM_CLOCK_KHZ 40000.0
#define PWM_STEPS 1000

static void *pwms[PWM_NUM] = {NULL};
static double pwm_shift = 0, pwm_multiplier = 0;

static void pwm_init_config() {
    int32_t status;
    uint16_t timing = getLoopTiming(&status);
    HAL_CHECK(status, "pwm subsystem critical failure");
    assert(timing != 0);
    pwm_multiplier = PWM_CLOCK_KHZ / timing;
    pwm_shift = PWM_STEPS - 1 - PWM_GEN_CENTER * pwm_multiplier;
}

void pwm_init(uint8_t pwm_id, uint8_t squelch, bool latch_pwm_zero) {
    assert(pwms[pwm_id] == NULL);
    int32_t status;
    void *port = initializeDigitalPort(getPort(pwm_id), &status);
    HAL_CHECK(status, "pwm subsystem critical failure");
    bool success = allocatePWMChannel(port, &status);
    HAL_CHECK(status, "pwm subsystem critical failure");
    if (!success) {
        panic("pwm subsystem critical failure (failed to allocate PWM channel)");
    }
    setPWM(port, 0, &status);
    HAL_CHECK(status, "pwm subsystem critical failure");
    setPWMPeriodScale(port, squelch, &status);
    HAL_CHECK(status, "pwm subsystem critical failure");
    if (latch_pwm_zero) { // TODO: find out why we skip this for servos
        latchPWMZero(port, &status);
        HAL_CHECK(status, "pwm subsystem critical failure");
    }
    pwms[pwm_id] = port;
}

void pwm_update(double millis, int pwm_id) {
    void *port = pwms[pwm_id];
    assert(port != NULL);
    unsigned short pwm_raw;
    if (isnan(millis)) {
        pwm_raw = 0;
    } else {
        pwm_raw = (unsigned short) (millis * pwm_multiplier + pwm_shift);
    }
    int32_t status;
    setPWM(port, pwm_raw, &status);
    HAL_CHECK(status, "pwm subsystem critical failure");
}


static void *solenoids[PCM_NUM][SOLENOID_NUM] = {{NULL}};

void solenoid_init(uint8_t pcm_id, uint8_t solenoid_id) {
    assert(solenoids[pcm_id] == NULL);
    int32_t status;
    solenoids[pcm_id][solenoid_id] = initializeSolenoidPort(getPortWithModule(pcm_id, solenoid_id), &status);
    HAL_CHECK(status, "solenoid subsystem critical failure");
}

void solenoid_update(bool on, uint8_t pcm_id, uint8_t solenoid_id) {
    void *port = solenoids[pcm_id][solenoid_id];
    assert(port != NULL);
    int32_t status;
    setSolenoid(port, on, &status);
    HAL_CHECK(status, "solenoid subsystem critical failure");
}


static void *gpios[GPIO_NUM] = {NULL};
static void *interrupts[INTERRUPT_NUM] = {NULL};
static pthread_t interrupt_threads[INTERRUPT_NUM];

void gpio_init_input_poll(int gpio_pin) {
    assert(gpios[gpio_pin] == NULL);
    int32_t status;
    void *port = initializeDigitalPort(getPort(gpio_pin), &status);
    HAL_CHECK(status, "gpio subsystem critical failure");
    allocateDIO(port, true, &status);
    HAL_CHECK(status, "gpio subsystem critical failure");
    gpios[gpio_pin] = port;
}

bool gpio_poll_input(int gpio_pin) {
    void *port = gpios[gpio_pin];
    assert(port != NULL);
    int32_t status;
    bool value = getDIO(port, &status);
    HAL_CHECK(status, "gpio subsystem critical failure");
    return value;
}

void gpio_init_input_interrupt(uint8_t gpio_pin, uint8_t interrupt_id) {
    assert(interrupts[interrupt_id] == NULL);
    gpio_init_input_poll(gpio_pin);
    int32_t status;
    void *port = initializeInterrupts(interrupt_id, true, &status); // true: synchronous, so we'll run our own thread
    HAL_CHECK(status, "gpio subsystem critical failure");
    requestInterrupts(port, 0, gpio_pin, false, &status); // false: digital
    HAL_CHECK(status, "gpio subsystem critical failure");
    setInterruptUpSourceEdge(port, true, true, &status); // both rising and falling edge
    HAL_CHECK(status, "gpio subsystem critical failure");
    interrupts[interrupt_id] = port;
}

struct interrupt_params {
    void *gpio_port;
    void *interrupt_port;
    callback cb;
    bool run; // TODO: eliminate or use
};

static void *gpio_interrupt_handler_thread(void*);

void gpio_start_interrupt(int gpio_pin, int interrupt_id, callback cb) {
    void *interrupt_port = interrupts[interrupt_id];
    assert(interrupt_port != NULL);
    void *gpio_port = gpios[gpio_pin];
    assert(gpio_port != NULL);
    struct interrupt_params *params = (struct interrupt_params *) malloc(sizeof(struct interrupt_params));
    if (params == NULL) {
        perror("malloc");
        panic("gpio subsystem critical failure");
    }
    params->gpio_port = gpio_port;
    params->interrupt_port = interrupt_port;
    params->cb = cb;
    params->run = true;
    if (pthread_create(&interrupt_threads[interrupt_id], NULL, gpio_interrupt_handler_thread, &params) != 0) {
        perror("pthread_create");
        panic("gpio subsystem critical failure");
    }
}

static void *gpio_interrupt_handler_thread(void *param) {
    struct interrupt_params *params = (struct interrupt_params *) param;
    while (params->run) {
        int32_t status;
        // TODO: optimize based on timing out or not - timed out if the return value is 0.
        waitForInterrupt(params->interrupt_port, 10.0, false, &status);
        HAL_CHECK(status, "gpio subsystem critical failure");
        queue_event(params->cb);
    }
    free(params);
    return NULL;
}
