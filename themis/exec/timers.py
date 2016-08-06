import threading
import time
import themis.exec.runloop
import heapq


def start_timer(millis: int, callback) -> None:
    seconds = millis / 1000.0
    threading.Thread(target=timer_thread_body, args=(seconds, callback)).start()


def timer_thread_body(seconds: float, callback) -> None:
    while True:
        # TODO: don't queue if the last event hasn't been processed yet?
        time.sleep(seconds)
        themis.exec.runloop.queue_event(callback)


_queue_cond = threading.Condition()
_queue = []


def start_proc_thread() -> None:
    threading.Thread(target=proc_thread_body).start()


def proc_thread_body() -> None:
    while True:
        with _queue_cond:
            while not _queue:
                _queue_cond.wait()
            # while the next target is in the future
            while _queue[0][0] > time.time():
                _queue_cond.wait(time.time() - _queue[0][0])
            target_time, callback = heapq.heappop(_queue)
            assert target_time <= time.time()
        themis.exec.runloop.queue_event(callback)


def run_after(seconds: float, callback) -> None:
    target_time = time.time() + seconds
    with _queue_cond:
        heapq.heappush(_queue, (target_time, callback))
        _queue_cond.notifyAll()
