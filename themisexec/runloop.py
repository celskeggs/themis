import typing
import queue

_run_queue = queue.Queue()
_loop_entered = False


def enter_loop(callback: typing.Callable[[], None]) -> None:
    global _loop_entered
    assert not _loop_entered
    _loop_entered = True

    queue_event(callback)
    while True:
        # TODO: exception handling? or is that unnecessary?
        callback = _run_queue.get()
        callback()


def queue_event(callback: typing.Callable[[], None]):
    # will never throw an exception, because it's an unbounded queue and will always have more room
    # TODO: warn if the queue gets too long?
    _run_queue.put_nowait(callback)
