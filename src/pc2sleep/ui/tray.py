"""System tray icon and menu."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon

from pc2sleep import autostart
from pc2sleep.config import AppConfig, get_app_data_dir, get_config_path
from pc2sleep.ui.icon import create_app_icon

logger = logging.getLogger(__name__)


class TrayController:
    """Manage system tray icon, menu, and notifications."""

    def __init__(self, config: AppConfig, on_quit) -> None:
        self._config = config
        self._on_quit = on_quit
        self._tray = QSystemTrayIcon(create_app_icon(), parent=None)
        self._tray.setToolTip("PC Sleep Service")
        self._build_menu()
        self._tray.activated.connect(self._on_activated)

    def show(self) -> None:
        self._tray.show()

    def notify(self, title: str, message: str, msecs: int = 8000) -> None:
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, msecs)

    def _build_menu(self) -> None:
        menu = QMenu()

        open_config = QAction("Открыть папку настроек", menu)
        open_config.triggered.connect(self._open_config_folder)
        menu.addAction(open_config)

        open_file = QAction("Открыть config.json", menu)
        open_file.triggered.connect(self._open_config_file)
        menu.addAction(open_file)

        show_token = QAction("Показать токен", menu)
        show_token.triggered.connect(self._show_token)
        menu.addAction(show_token)

        menu.addSeparator()

        self._autostart_action = QAction("Запускать при старте Windows", menu)
        self._autostart_action.setCheckable(True)
        self._autostart_action.setChecked(autostart.is_autostart_enabled())
        self._autostart_action.triggered.connect(self._toggle_autostart)
        menu.addAction(self._autostart_action)

        menu.addSeparator()

        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_token()

    def _open_config_folder(self) -> None:
        path = get_app_data_dir()
        self._open_path(path)

    def _open_config_file(self) -> None:
        self._open_path(get_config_path())

    def _open_path(self, path: Path) -> None:
        try:
            if sys.platform == "win32":
                import os

                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception:
            logger.exception("Failed to open path: %s", path)

    def show_token_dialog(self) -> None:
        self._show_token()

    def _show_token(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(self._config.token)

        QMessageBox.information(
            None,
            "Токен доступа",
            "Токен скопирован в буфер обмена.\n\n"
            f"{self._config.token}\n\n"
            "Пример запроса:\n"
            f"http://<IP_ПК>:{self._config.port}/sleep?token={self._config.token}",
        )

    def _toggle_autostart(self, checked: bool) -> None:
        try:
            autostart.set_autostart(checked)
            self._autostart_action.setChecked(autostart.is_autostart_enabled())
            state = "включена" if checked else "отключена"
            self.notify("Автозагрузка", f"Автозагрузка {state}")
        except Exception as exc:
            logger.exception("Failed to toggle autostart")
            self._autostart_action.setChecked(autostart.is_autostart_enabled())
            QMessageBox.warning(None, "Ошибка", f"Не удалось изменить автозагрузку:\n{exc}")
