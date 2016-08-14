#include <time.h>
#include <sys/types.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <errno.h>
#include "themis.h"

#define PTHREAD_CHECK(call, ...) if (call(__VA_ARGS__) != 0) { perror(#call); panic("timer subsystem critical failure"); }

static uint64_t get_time_nanos() {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &t) != 0) {
        perror("clock_gettime");
        panic("critical failure in timer subsystem");
    }
    return t.tv_sec * UINT64_C(1000000000) + t.tv_nsec;
}

struct periodic_timer {
    uint32_t period_ns;
    uint64_t next_tick_ns;
    callback cb;
};

struct one_shot_timer {
    uint64_t happen_at_ns;
    callback cb;
    struct one_shot_timer *next;
};

static void *timer_body(void *);

static pthread_t timer_thread;
static bool timer_init_complete = false;
static bool timer_loop_run = true; // TODO: eliminate or use

static struct periodic_timer *periodic_timers = NULL;
static int periodic_timer_count = 0;
static int periodic_timer_capacity = 0;
// TODO: use a datastructure that doesn't require O(n) time for insertion
static pthread_mutex_t next_shot_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t next_shot_cond = PTHREAD_COND_INITIALIZER;
static struct one_shot_timer *next_one_shot_timer = NULL;

void begin_timers() {
    if (pthread_create(&timer_thread, NULL, timer_body, NULL) != 0) {
        perror("pthread_create");
        panic("critical failure in timer subsystem");
    }
    timer_init_complete = true;
}

// NOT THREADSAFE. Can only be used before begin_timers.
void start_timer_ns(uint32_t period_ns, callback cb) {
    assert(!timer_init_complete);
    if (periodic_timer_count >= periodic_timer_capacity) {
        periodic_timer_capacity = periodic_timer_capacity ? periodic_timer_capacity * 2 : 8;
        periodic_timers = realloc(periodic_timers, periodic_timer_capacity * sizeof(struct periodic_timer));
    }
    periodic_timers[periodic_timer_count++].period_ns = period_ns;
}

void run_after_ns(uint32_t delay_ns, callback cb) {
    uint64_t now = get_time_nanos();
    struct one_shot_timer *timer = malloc(sizeof(struct one_shot_timer));
    if (timer == NULL) {
        perror("malloc");
        panic("timer subsystem critical failure");
    }
    timer->cb = cb;
    timer->happen_at_ns = now + delay_ns;
    PTHREAD_CHECK(pthread_mutex_lock, &next_shot_mutex);
#define RUN_ORDER_LT(a, b) ((int64_t) (a->happen_at_ns - now) < (int64_t) (b->happen_at_ns - now))
    // we need to insert this in the correct sorted order (note that the sort order is based on the current time)
    if (next_one_shot_timer == NULL || RUN_ORDER_LT(timer, next_one_shot_timer)) {
        timer->next = next_one_shot_timer;
        next_one_shot_timer = timer;
    } else {
        // search to find the correct timer for us to go after
        struct one_shot_timer *cur = next_one_shot_timer;
        while (cur->next != NULL && RUN_ORDER_LT(cur->next, timer)) {
            cur = cur->next;
        }
        timer->next = cur->next;
        cur->next = timer;
    }
#undef RUN_ORDER_LT
    pthread_cond_signal(&next_shot_cond);
    PTHREAD_CHECK(pthread_mutex_unlock, &next_shot_mutex);
}

static void *timer_body(void *unused_param) {
    uint64_t base_time = get_time_nanos();
    for (int i = 0; i < periodic_timer_count; i++) {
        periodic_timers[i].next_tick_ns = base_time + periodic_timers[i].period_ns;
    }
    while (timer_loop_run) {
        uint64_t now = get_time_nanos();
        int64_t shortest_remaining = INT64_C(10000000000); // don't sleep longer than ten seconds at a time
        // process any ready periodic timers
        for (int i = 0; i < periodic_timer_count; i++) {
            int64_t remaining = (int64_t) (periodic_timers[i].next_tick_ns - now);
            if (remaining <= 0) {
                // TODO: make sure we don't enqueue this too many times
                queue_event(periodic_timers[i].cb);
                periodic_timers[i].next_tick_ns += periodic_timers[i].period_ns;
                remaining = (int64_t) (periodic_timers[i].next_tick_ns - now);
            }
            if (remaining < shortest_remaining) {
                shortest_remaining = remaining;
            }
        }
        // process any ready one-off timers
        PTHREAD_CHECK(pthread_mutex_lock, &next_shot_mutex);
        while (next_one_shot_timer != NULL && (int64_t) (next_one_shot_timer->happen_at_ns - now) <= 0) {
            struct one_shot_timer *t = next_one_shot_timer;
            next_one_shot_timer = t->next;
            PTHREAD_CHECK(pthread_mutex_unlock, &next_shot_mutex);
            // make sure we release the lock before queueing
            queue_event(t->cb);
            free(t);
            // note that the next timer list could have changed during this time, so we'll need to go back to the global
            PTHREAD_CHECK(pthread_mutex_lock, &next_shot_mutex);
        }
        if (next_one_shot_timer != NULL) {
            int64_t remaining = (int64_t) (next_one_shot_timer->happen_at_ns - now);
            if (remaining < shortest_remaining) {
                shortest_remaining = remaining;
            }
        }
        // sleep until the next timer is ready to be processed
        if (shortest_remaining > 0) {
            // the locks and unlocks and enqueueings could have invalidated this offset, so make sure we don't sleep a bunch more than necessary
            uint64_t new_now = get_time_nanos();
            int64_t new_remaining = shortest_remaining + (int64_t) (new_now - now);
            if (new_remaining > 0) {
                struct timespec t;
                t.tv_sec = new_remaining / 1000000000;
                t.tv_nsec = new_remaining % 1000000000;
                if (pthread_cond_timedwait(&next_shot_cond, &next_shot_mutex, &t) != 0 && errno != ETIMEDOUT) {
                    perror("pthread_cond_timedwait");
                    panic("timer subsystem critical failure");
                }
                // at this point, we either have new timers added or have a timer that should be enqueued now
            }
        }
        PTHREAD_CHECK(pthread_mutex_unlock, &next_shot_mutex);
    }
    return NULL;
}
