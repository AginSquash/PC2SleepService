"""Tests for network bind resolution."""

from __future__ import annotations

import pytest

from pc2sleep.network import resolve_bind_hosts


def test_resolve_bind_all_interfaces():
    assert resolve_bind_hosts("0.0.0.0") == ["0.0.0.0"]


def test_resolve_bind_specific_ip():
    assert resolve_bind_hosts("192.168.1.50") == ["192.168.1.50"]


def test_resolve_bind_invalid_ip():
    with pytest.raises(ValueError):
        resolve_bind_hosts("not-an-ip")


def test_resolve_bind_auto_uses_lan_addresses(monkeypatch):
    monkeypatch.setattr(
        "pc2sleep.network.get_lan_ipv4_addresses",
        lambda: ["192.168.1.10", "10.0.0.5"],
    )
    assert resolve_bind_hosts("auto") == ["192.168.1.10", "10.0.0.5"]


def test_resolve_bind_auto_fallback(monkeypatch):
    monkeypatch.setattr("pc2sleep.network.get_lan_ipv4_addresses", lambda: [])
    assert resolve_bind_hosts("auto") == ["0.0.0.0"]
