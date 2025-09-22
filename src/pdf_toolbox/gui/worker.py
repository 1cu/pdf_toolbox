"""Worker thread for running actions (GUI-only)."""

from __future__ import annotations

import inspect
from threading import Event

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    """Run an action in a background thread with cooperative cancellation."""

    finished = Signal(object)
    error = Signal(object)

    def __init__(self, func, kwargs: dict[str, object]):
        """Initialize worker with the callable and keyword arguments."""
        super().__init__()
        self.func = func
        self.kwargs = kwargs
        self._cancel = Event()

    def cancel(self) -> None:
        """Request cancellation; the worker checks cooperatively."""
        self._cancel.set()

    def run(self) -> None:
        """Execute the action and emit results or errors."""
        try:
            if "cancel" in inspect.signature(self.func).parameters:
                self.kwargs.setdefault("cancel", self._cancel)
            result = self.func(**self.kwargs)
            if not self._cancel.is_set():
                self.finished.emit(result)
        except Exception as exc:
            if not self._cancel.is_set():
                self.error.emit(exc)


__all__ = ["Worker"]
