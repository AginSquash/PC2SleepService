"""Windows system actions: sleep, shutdown, minimize all windows."""

from __future__ import annotations

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


def minimize_all() -> None:
    """Minimize all open windows via Shell.Application COM."""
    if sys.platform != "win32":
        logger.debug("minimize_all skipped (not Windows)")
        return

    import comtypes.client

    shell = comtypes.client.CreateObject("Shell.Application")
    shell.MinimizeAll()


def sleep_pc() -> None:
    """Put the system into sleep/suspend state."""
    if sys.platform != "win32":
        logger.debug("sleep_pc skipped (not Windows)")
        return

    import ctypes

    # SetSuspendState(Hibernate=False, ForceCritical=False, DisableWakeEvent=False)
    result = ctypes.windll.powrprof.SetSuspendState(0, 0, 0)
    if not result:
        raise OSError("SetSuspendState failed")


def shutdown_pc() -> None:
    """Shut down the system immediately."""
    if sys.platform != "win32":
        logger.debug("shutdown_pc skipped (not Windows)")
        return

    subprocess.run(
        ["shutdown", "/s", "/t", "0"],
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
