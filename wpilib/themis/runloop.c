#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <assert.h>
#include "themis.h"

struct queue_entry {
    struct queue_entry *next_in_queue;
    callback cb;
};

static pthread_mutex_t queue_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t queue_cond = PTHREAD_COND_INITIALIZER;

// read from head; write to tail
static struct queue_entry *queue_head = NULL;
static struct queue_entry *queue_tail = NULL;

#define PTHREAD_CHECK(call, ...) if (call(__VA_ARGS__) != 0) { perror(#call); panic("runloop critical failure"); }

void enter_loop(callback entry) {
    queue_event(entry);
    while (true) {
        PTHREAD_CHECK(pthread_mutex_lock, &queue_lock);
        while (queue_head == NULL) {
            assert(queue_tail == NULL);
            PTHREAD_CHECK(pthread_cond_wait, &queue_cond, &queue_lock);
        }
        struct queue_entry *old = queue_head;
        queue_head = old->next_in_queue;
        if (queue_head == NULL) {
            assert(old == queue_tail);
            queue_tail = NULL;
        }
        PTHREAD_CHECK(pthread_mutex_unlock, &queue_lock);
        callback target = old->cb;
        free(old);
        // now, while we don't hold the lock, dispatch to the callback.
        target();
    }
}

// TODO: have a maximum length for the queue?
void queue_event(callback cb) {
    struct queue_entry *ent = (struct queue_entry *) malloc(sizeof(struct queue_entry));
    if (ent == NULL) {
        perror("malloc");
        panic("runloop critical failure");
    }
    ent->cb = cb;
    ent->next_in_queue = NULL;
    PTHREAD_CHECK(pthread_mutex_lock, &queue_lock);
    if (queue_tail == NULL) {
        assert(queue_head == NULL);
        queue_tail = queue_head = ent;
    } else {
        assert(queue_head != NULL);
        queue_tail = queue_tail->next_in_queue = ent;
    }
    PTHREAD_CHECK(pthread_cond_signal, &queue_cond);
    PTHREAD_CHECK(pthread_mutex_unlock, &queue_lock);
    return; // success!
}
