"""PC2Sleep application entrypoint."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtWidgets import QApplication, QMessageBox

from pc2sleep.config import ensure_app_dir, get_config_path, get_log_path, load_config
from pc2sleep.server import ActionEmitter, HTTPServerThread, RequestState
from pc2sleep.single_instance import SingleInstanceLock
from pc2sleep.ui.countdown import CountdownDialog
from pc2sleep.ui.tray import TrayController


def setup_logging() -> None:
    ensure_app_dir()
    log_path = get_log_path()

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)


class Application:
    """Orchestrates tray, HTTP server, and countdown UI."""

    def __init__(self) -> None:
        self._config = load_config()
        self._emitter = ActionEmitter()
        self._request_state = RequestState(self._config.rate_limit_seconds)
        self._http = HTTPServerThread(self._config, self._emitter, self._request_state)
        self._countdown: CountdownDialog | None = None
        self._tray: TrayController | None = None

        self._emitter.action_requested.connect(self._on_action_requested)

    def start(self, *, first_run: bool = False) -> None:
        self._http.start()
        self._tray = TrayController(self._config, on_quit=QApplication.instance().quit)
        self._tray.show()

        if first_run:
            self._tray.notify(
                "PC Sleep Service",
                "Сервис запущен. Токен скопирован — откройте меню трея → «Показать токен».",
            )
            self._tray.show_token_dialog()

        if self._config.bind == "0.0.0.0":
            logging.getLogger(__name__).warning(
                "Server binds to 0.0.0.0 — доступен всем интерфейсам. "
                "Не пробрасывайте порт в интернет без TLS."
            )

    def stop(self) -> None:
        self._http.stop()

    def _on_action_requested(self, action: str) -> None:
        if self._countdown is not None and self._countdown.isVisible():
            return

        self._request_state.set_countdown_active(True)

        self._countdown = CountdownDialog(
            action=action,
            countdown_seconds=self._config.countdown_seconds,
            on_finished=self._on_countdown_finished,
        )
        self._countdown.show()

    def _on_countdown_finished(self) -> None:
        self._request_state.set_countdown_active(False)
        if self._countdown:
            self._countdown.deleteLater()
            self._countdown = None


def main() -> int:
    setup_logging()
    logger = logging.getLogger(__name__)

    lock = SingleInstanceLock()
    if not lock.acquire():
        app = QApplication(sys.argv)
        QMessageBox.warning(
            None,
            "PC Sleep Service",
            "Приложение уже запущено.",
        )
        return 1

    first_run = not get_config_path().exists()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("PCSleepService")

    try:
        application = Application()
        application.start(first_run=first_run)
    except OSError as exc:
        logger.exception("Failed to start HTTP server")
        QMessageBox.critical(
            None,
            "PC Sleep Service",
            f"Не удалось запустить HTTP-сервер:\n{exc}",
        )
        lock.release()
        return 1

    exit_code = app.exec()
    application.stop()
    lock.release()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
