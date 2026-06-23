"""HTTP server for remote sleep/shutdown triggers."""

from __future__ import annotations

import hmac
import ipaddress
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Callable
from urllib.parse import parse_qs, urlparse

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from pc2sleep.config import AppConfig

logger = logging.getLogger(__name__)

ActionCallback = Callable[[str], tuple[int, str]]


class ActionEmitter(QObject):
    """Thread-safe bridge from HTTP worker threads to Qt main thread."""

    action_requested = Signal(str)


class RequestState:
    """Shared mutable state guarded by a lock."""

    def __init__(self, rate_limit_seconds: int) -> None:
        self._lock = threading.Lock()
        self._rate_limit_seconds = rate_limit_seconds
        self._last_request_at = 0.0
        self._countdown_active = False

    def try_begin_request(self) -> tuple[bool, str | None]:
        with self._lock:
            now = time.monotonic()
            if self._countdown_active:
                return False, "countdown_active"
            if self._rate_limit_seconds > 0:
                elapsed = now - self._last_request_at
                if elapsed < self._rate_limit_seconds:
                    return False, "rate_limited"
            self._last_request_at = now
            return True, None

    def set_countdown_active(self, active: bool) -> None:
        with self._lock:
            self._countdown_active = active


def _client_ip(handler: BaseHTTPRequestHandler) -> str:
    forwarded = handler.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return handler.client_address[0]


def _is_ip_allowed(ip_str: str, allowed_cidrs: list[str]) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    for cidr in allowed_cidrs:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        if ip in network:
            return True
    return False


def _validate_token(provided: str | None, expected: str) -> bool:
    if not provided:
        return False
    return hmac.compare_digest(provided, expected)


class PCSleepRequestHandler(BaseHTTPRequestHandler):
    """Handle GET /sleep, /shutdown, /ping."""

    config: AppConfig
    emitter: ActionEmitter
    request_state: RequestState

    def log_message(self, format: str, *args: object) -> None:
        logger.info("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        token = query.get("token", [None])[0]

        client_ip = _client_ip(self)

        if not _is_ip_allowed(client_ip, self.config.allowed_cidrs):
            self._respond(403, "forbidden")
            return

        if not _validate_token(token, self.config.token):
            time.sleep(1)
            self._respond(401, "unauthorized")
            return

        if path == "/ping":
            self._respond(200, "ok")
            return

        if path not in ("/sleep", "/shutdown"):
            self._respond(404, "not_found")
            return

        allowed, reason = self.request_state.try_begin_request()
        if not allowed:
            self._respond(409, reason or "conflict")
            return

        action = "sleep" if path == "/sleep" else "shutdown"
        self.emitter.action_requested.emit(action)
        self._respond(202, "accepted")

    def _respond(self, status: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class HTTPServerThread:
    """Run ThreadingHTTPServer in a background daemon thread."""

    def __init__(
        self,
        config: AppConfig,
        emitter: ActionEmitter,
        request_state: RequestState,
    ) -> None:
        self._config = config
        self._emitter = emitter
        self._request_state = request_state
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        handler = type(
            "BoundPCSleepRequestHandler",
            (PCSleepRequestHandler,),
            {
                "config": self._config,
                "emitter": self._emitter,
                "request_state": self._request_state,
            },
        )
        self._server = ThreadingHTTPServer(
            (self._config.bind, self._config.port),
            handler,
        )
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="pc2sleep-http",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "HTTP server listening on %s:%s",
            self._config.bind,
            self._config.port,
        )

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
