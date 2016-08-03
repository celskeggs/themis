import threading


class Parameter:
    def __init__(self, default_value):
        self._default_value = default_value
        self._local = threading.local()

    def get(self):
        return getattr(self._local, "value", self._default_value)

    def _swap(self, value):
        old, self._local.value = self.get(), value
        return old

    def parameterize(self, value) -> "Parameterization":
        return Parameterization(self._swap, value)


class Parameterization:
    def __init__(self, swap, value):
        self._swap = swap
        self._value = value
        self._inside = False
        self._saved_value = None

    def __enter__(self) -> None:
        assert not self._inside
        self._inside = True
        self._saved_value = self._swap(self._value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self._inside
        self._inside = False
        assert self._swap(self._saved_value)
