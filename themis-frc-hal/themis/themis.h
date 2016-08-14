#ifndef THEMIS_H
#define THEMIS_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*callback)(void);

// runloop.c
void enter_loop(callback entry);
void queue_event(callback cb);

// timers.c
void start_timer_ns(uint32_t period_ns, callback cb);
void begin_timers();
void run_after_ns(uint32_t delay_ns, callback cb);

// themis.c
void panic(const char *err) __attribute__ ((__noreturn__));
void do_nothing(void);
double deadzone(double value, double zone);
double choose_float(bool cond, double a, double b);
double pwm_map(double value, double rev_max, double rev_min, double center, double fwd_min, double fwd_max);
double ramping_update(double previous, double target, double max_change_per_update);

// frc.c
void ds_init(void);
void ds_begin(callback target);
int get_robot_mode();
double get_joystick_axis(int joy_i, int axis);
bool get_joystick_button(int joy_i, int btn);
void pwm_init(uint8_t pwm_id, uint8_t squelch, bool latch_pwm_zero);
void pwm_update(double millis, int pwm_id);
void solenoid_init(uint8_t pcm_id, uint8_t solenoid_id);
void solenoid_update(bool on, uint8_t pcm_id, uint8_t solenoid_id);
void gpio_init_input_poll(int gpio_pin);
bool gpio_poll_input(int gpio_pin);
void gpio_init_input_interrupt(uint8_t gpio_pin, uint8_t interrupt_id);
void gpio_start_interrupt(int gpio_pin, int interrupt_id, callback cb);

#ifdef __cplusplus
}
#endif

#endif //THEMIS_H
