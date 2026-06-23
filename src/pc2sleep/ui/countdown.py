"""Countdown warning dialog before sleep/shutdown."""

from __future__ import annotations

import logging
import sys
from typing import Callable

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pc2sleep import actions

logger = logging.getLogger(__name__)

ACTION_LABELS = {
    "sleep": "The PC will go to sleep",
    "shutdown": "The PC will shut down",
}


class CountdownDialog(QDialog):
    """Topmost modal countdown with cancel."""

    cancelled = Signal()
    completed = Signal(str)

    def __init__(
        self,
        action: str,
        countdown_seconds: int,
        on_finished: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._action = action
        self._remaining = countdown_seconds
        self._total = countdown_seconds
        self._on_finished = on_finished

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.Dialog
        )
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()
        self._center_on_screen()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("container")
        container.setFixedWidth(480)
        outer.addWidget(container)

        container.setStyleSheet(
            """
            QFrame#container {
                background-color: #1e1e2e;
                border: 2px solid #f38ba8;
                border-radius: 12px;
            }
            QLabel {
                color: #cdd6f4;
                background: transparent;
            }
            QLabel#title {
                color: #f38ba8;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel#countdown {
                color: #fab387;
                font-size: 48px;
                font-weight: bold;
                min-height: 58px;
            }
            QPushButton#cancel {
                background-color: #a6e3a1;
                color: #11111b;
                border: none;
                border-radius: 20px;
                padding: 10px 32px;
                font-size: 15px;
                font-weight: bold;
                min-width: 140px;
                min-height: 42px;
            }
            QPushButton#cancel:hover {
                background-color: #94e2d5;
            }
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #313244;
                min-height: 10px;
                max-height: 10px;
            }
            QProgressBar::chunk {
                background-color: #f38ba8;
                border-radius: 4px;
            }
            """
        )

        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Warning!")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        action_label = ACTION_LABELS.get(self._action, "Action will be performed")
        subtitle = QLabel(f"{action_label} in:")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._countdown_label = QLabel(str(self._remaining))
        self._countdown_label.setObjectName("countdown")
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown_label.setMinimumHeight(58)

        self._progress = QProgressBar()
        self._progress.setRange(0, self._total)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)

        hint = QLabel('Press "Cancel" to stop')
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel")
        cancel_btn.setMinimumSize(140, 42)
        cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._countdown_label)
        layout.addWidget(self._progress)
        layout.addWidget(hint)
        layout.addLayout(btn_row)

        container.adjustSize()
        self.setFixedSize(container.size())

    def _center_on_screen(self) -> None:
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2,
            )

    def _force_foreground(self) -> None:
        if sys.platform != "win32":
            self.raise_()
            self.activateWindow()
            return

        import ctypes

        user32 = ctypes.windll.user32
        ASFW_ANY = 0xFFFFFFFF
        user32.AllowSetForegroundWindow(ASFW_ANY)
        hwnd = int(self.winId())
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        user32.SwitchToThisWindow(hwnd, True)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        try:
            actions.minimize_all()
        except Exception:
            logger.exception("Failed to minimize all windows")
        self._force_foreground()
        self._timer.start()

    def _tick(self) -> None:
        self._remaining -= 1
        elapsed = self._total - self._remaining
        self._countdown_label.setText(str(max(0, self._remaining)))
        self._progress.setValue(elapsed)

        if self._remaining <= 0:
            self._timer.stop()
            self._execute_action()
            self.completed.emit(self._action)
            if self._on_finished:
                self._on_finished()
            self.accept()

    def _execute_action(self) -> None:
        try:
            if self._action == "sleep":
                actions.sleep_pc()
            elif self._action == "shutdown":
                actions.shutdown_pc()
        except Exception:
            logger.exception("Failed to execute action: %s", self._action)

    def _on_cancel(self) -> None:
        self._timer.stop()
        self.cancelled.emit()
        if self._on_finished:
            self._on_finished()
        self.reject()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(event)
