"""Tests for configuration module."""

from __future__ import annotations

import json

import pytest

from pc2sleep.config import AppConfig, get_config_path, load_config, save_config


def test_default_config_validates():
    config = AppConfig(token="a" * 32)
    config.validate()


def test_invalid_token_raises():
    config = AppConfig(token="short")
    with pytest.raises(ValueError, match="token"):
        config.validate()


def test_invalid_port_raises():
    config = AppConfig(token="a" * 32, port=0)
    with pytest.raises(ValueError, match="port"):
        config.validate()


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("pc2sleep.config.get_app_data_dir", lambda: tmp_path)
    config = AppConfig(token="test-token-" + "x" * 16, port=9999)
    save_config(config)

    loaded = load_config()
    assert loaded.token == config.token
    assert loaded.port == 9999


def test_load_creates_config_on_first_run(tmp_path, monkeypatch):
    monkeypatch.setattr("pc2sleep.config.get_app_data_dir", lambda: tmp_path)
    assert not get_config_path().exists()

    config = load_config()
    assert get_config_path().exists()
    assert len(config.token) >= 16

    with get_config_path().open(encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["token"] == config.token
