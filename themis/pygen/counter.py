import threading


class Counter:
    def __init__(self):
        self._ctr = 0
        self._lock = threading.Lock()

    def next(self):
        with self._lock:
            value = self._ctr
            self._ctr += 1
            return value

    def nstr(self, format):
        return format % (self.next(),)
