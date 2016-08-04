import threading
import time
import themis.exec.runloop


def start_timer(millis: int, callback) -> None:
    seconds = millis / 1000.0
    threading.Thread(target=timer_thread_body, args=(seconds, callback)).start()


def timer_thread_body(seconds: float, callback) -> None:
    while True:
        # TODO: don't queue if the last event hasn't been processed yet?
        time.sleep(seconds)
        themis.exec.runloop.queue_event(callback)
