"""Tests for HTTP server logic."""

from __future__ import annotations

import threading
import urllib.error
import urllib.request

import pytest
from PySide6.QtWidgets import QApplication

from pc2sleep.config import AppConfig
from pc2sleep.server import (
    ActionEmitter,
    HTTPServerThread,
    RequestState,
    _is_ip_allowed,
    _validate_token,
)


@pytest.fixture
def test_config():
    return AppConfig(
        token="super-secret-test-token-value",
        port=0,
        bind="127.0.0.1",
        allowed_cidrs=["127.0.0.0/8", "::1/128"],
        rate_limit_seconds=0,
    )


@pytest.fixture
def http_server(qapp, test_config):
    emitter = ActionEmitter()
    state = RequestState(test_config.rate_limit_seconds)
    server = HTTPServerThread(test_config, emitter, state)
    server.start()
    host, port = server._servers[0].server_address
    test_config.port = port
    yield server, emitter, state, host, port
    server.stop()


def _get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def test_is_ip_allowed_private():
    assert _is_ip_allowed("192.168.1.10", ["192.168.0.0/16"])
    assert not _is_ip_allowed("8.8.8.8", ["192.168.0.0/16"])


def test_validate_token():
    token = "my-secret-token"
    assert _validate_token(token, token)
    assert not _validate_token("wrong", token)
    assert not _validate_token(None, token)


def test_ping_ok(http_server, test_config):
    _, _, _, host, port = http_server
    status, body = _get(
        f"http://{host}:{port}/ping?token={test_config.token}",
    )
    assert status == 200
    assert body == "ok"


def test_unauthorized_wrong_token(http_server, test_config):
    _, _, _, host, port = http_server
    status, body = _get(f"http://{host}:{port}/ping?token=bad")
    assert status == 401
    assert body == "unauthorized"


def test_sleep_accepted(http_server, test_config):
    server, emitter, _, host, port = http_server
    received: list[str] = []
    done = threading.Event()

    def on_action(action: str) -> None:
        received.append(action)
        done.set()

    emitter.action_requested.connect(on_action)
    status, body = _get(
        f"http://{host}:{port}/sleep?token={test_config.token}",
    )
    assert status == 202
    assert body == "accepted"
    for _ in range(50):
        QApplication.processEvents()
        if done.wait(timeout=0.05):
            break
    assert received == ["sleep"]


def test_conflict_when_countdown_active(http_server, test_config):
    _, _, state, host, port = http_server
    state.set_countdown_active(True)
    status, body = _get(
        f"http://{host}:{port}/sleep?token={test_config.token}",
    )
    assert status == 409
    assert body == "countdown_active"
