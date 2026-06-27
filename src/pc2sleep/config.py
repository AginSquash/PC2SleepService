"""Application configuration load/save."""

from __future__ import annotations

import ipaddress
import json
import os
import secrets
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

APP_DIR_NAME = "PCSleepService"
CONFIG_FILE_NAME = "config.json"

DEFAULT_ALLOWED_CIDRS = [
    "127.0.0.0/8",
    "192.168.0.0/16",
    "10.0.0.0/8",
    "172.16.0.0/12",
]


def get_app_data_dir() -> Path:
    """Return per-user application data directory."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if not base:
            base = str(Path.home() / "AppData" / "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base) / APP_DIR_NAME


def get_config_path() -> Path:
    return get_app_data_dir() / CONFIG_FILE_NAME


def get_log_path() -> Path:
    return get_app_data_dir() / "pc2sleep.log"


@dataclass
class AppConfig:
    token: str
    port: int = 8765
    bind: str = "auto"
    countdown_seconds: int = 60
    allowed_cidrs: list[str] = field(default_factory=lambda: list(DEFAULT_ALLOWED_CIDRS))
    rate_limit_seconds: int = 5
    logging_enabled: bool = True
    log_max_bytes: int = 1_000_000
    log_backup_count: int = 2
    log_ping_requests: bool = False

    def validate(self) -> None:
        if not self.token or len(self.token) < 16:
            raise ValueError("token must be at least 16 characters")
        if not (1 <= self.port <= 65535):
            raise ValueError("port must be between 1 and 65535")
        if self.countdown_seconds < 1:
            raise ValueError("countdown_seconds must be >= 1")
        if self.rate_limit_seconds < 0:
            raise ValueError("rate_limit_seconds must be >= 0")
        if not self.allowed_cidrs:
            raise ValueError("allowed_cidrs must not be empty")
        if self.log_max_bytes < 10_000:
            raise ValueError("log_max_bytes must be >= 10000")
        if self.log_backup_count < 0:
            raise ValueError("log_backup_count must be >= 0")
        self._validate_bind()

    def _validate_bind(self) -> None:
        if self.bind in ("0.0.0.0", "auto"):
            return
        try:
            ipaddress.ip_address(self.bind)
        except ValueError as exc:
            raise ValueError("bind must be 'auto', '0.0.0.0', or a valid IP address") from exc

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def _restrict_file_permissions(path: Path) -> None:
    """Best-effort restrict config to current user."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def ensure_app_dir() -> Path:
    app_dir = get_app_data_dir()
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def load_config() -> AppConfig:
    """Load config from disk; create with generated token if missing."""
    ensure_app_dir()
    path = get_config_path()
    if not path.exists():
        config = AppConfig(token=_generate_token())
        save_config(config)
        return config

    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    config = AppConfig.from_dict(data)
    config.validate()
    return config


def save_config(config: AppConfig) -> None:
    """Persist config to disk."""
    config.validate()
    ensure_app_dir()
    path = get_config_path()
    with path.open("w", encoding="utf-8") as fh:
        json.dump(config.to_dict(), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    _restrict_file_permissions(path)
