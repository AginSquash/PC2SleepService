"""Windows registry autostart management."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_VALUE_NAME = "PCSleepService"


def _executable_path() -> str:
    import sys

    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())
    return f'"{Path(sys.executable).resolve()}" -m pc2sleep'


def is_autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_VALUE_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError as exc:
        logger.warning("Failed to read autostart registry: %s", exc)
        return False


def set_autostart(enabled: bool) -> None:
    if sys.platform != "win32":
        raise RuntimeError("Autostart is only supported on Windows")

    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        RUN_KEY,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, APP_VALUE_NAME, 0, winreg.REG_SZ, _executable_path())
        else:
            try:
                winreg.DeleteValue(key, APP_VALUE_NAME)
            except FileNotFoundError:
                pass
