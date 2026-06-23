"""PC2Sleep application entrypoint."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtWidgets import QApplication, QMessageBox

from pc2sleep.config import AppConfig, ensure_app_dir, get_config_path, get_log_path, load_config
from pc2sleep.server import ActionEmitter, HTTPServerThread, RequestState
from pc2sleep.single_instance import SingleInstanceLock
from pc2sleep.ui.countdown import CountdownDialog
from pc2sleep.ui.tray import TrayController


def setup_logging(config: AppConfig) -> None:
    root = logging.getLogger()
    root.handlers.clear()

    if not config.logging_enabled:
        logging.disable(logging.CRITICAL)
        return

    logging.disable(logging.NOTSET)
    ensure_app_dir()
    log_path = get_log_path()

    root.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=config.log_max_bytes,
        backupCount=config.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)


class Application:
    """Orchestrates tray, HTTP server, and countdown UI."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
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
                "Service started. Token copied — open tray menu → Show token.",
            )
            self._tray.show_token_dialog()

        if self._config.bind == "0.0.0.0":
            logging.getLogger(__name__).warning(
                "Server binds to 0.0.0.0 — accessible on all interfaces. "
                "Do not expose this port to the internet without TLS."
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
    logger = logging.getLogger(__name__)

    lock = SingleInstanceLock()
    if not lock.acquire():
        app = QApplication(sys.argv)
        QMessageBox.warning(
            None,
            "PC Sleep Service",
            "Application is already running.",
        )
        return 1

    first_run = not get_config_path().exists()
    config = load_config()
    setup_logging(config)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("PCSleepService")

    try:
        application = Application(config)
        application.start(first_run=first_run)
    except OSError as exc:
        logger.exception("Failed to start HTTP server")
        QMessageBox.critical(
            None,
            "PC Sleep Service",
            f"Failed to start HTTP server:\n{exc}",
        )
        lock.release()
        return 1

    exit_code = app.exec()
    application.stop()
    lock.release()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
