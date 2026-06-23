"""Single-instance guard via Windows named mutex."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

MUTEX_NAME = "Global\\PCSleepService_v1"
ERROR_ALREADY_EXISTS = 183


class SingleInstanceLock:
    """Hold a named mutex for the lifetime of the application."""

    def __init__(self) -> None:
        self._handle: int | None = None

    def acquire(self) -> bool:
        if sys.platform != "win32":
            return True

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, wintypes.BOOL(True), MUTEX_NAME)
        if not handle:
            return False

        last_error = kernel32.GetLastError()
        if last_error == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False

        self._handle = handle
        return True

    def release(self) -> None:
        if self._handle is not None and sys.platform == "win32":
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(self, *_args: object) -> None:
        self.release()
