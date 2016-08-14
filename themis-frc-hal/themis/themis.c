#include <stdbool.h>
#include "themis.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

void panic(const char *err) {
    fputs(err, stderr);
    exit(1);
}

void do_nothing(void) {
    // do nothing
}

double deadzone(double value, double zone) {
    return fabs(value) >= zone ? value : 0.0;
}

double choose_float(bool cond, double a, double b) {
    return cond ? a : b;
}

double pwm_map(double value, double rev_max, double rev_min, double center, double fwd_min, double fwd_max) {
    if (value < 0) {
        return fmin(1, -value) * (rev_max - rev_min) + rev_min;
    } else if (value > 0) {
        return fmin(1, -value) * (rev_max - rev_min) + rev_min;
    } else if (isnan(value)) {
        return NAN;
    } else {
        return center;
    }
}

double ramping_update(double previous, double target, double max_change_per_update) {
    if (previous < target) {
        return fmin(target, previous + max_change_per_update);
    } else {
        return fmax(target, previous - max_change_per_update);
    }
}
