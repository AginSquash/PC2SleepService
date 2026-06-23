# Conventions

## Code

- `src/pc2sleep/` — package root
- WinAPI only in `actions.py`, `autostart.py`, `single_instance.py`
- On non-Windows, WinAPI calls are no-op / skipped (for tests on macOS)

## Security

- Token: `secrets.token_urlsafe(32)`, comparison via `hmac.compare_digest`
- Token only in query (`?token=`) — by design; risk of logs/browser history
- HTTP without TLS — LAN only
- `allowed_cidrs`: RFC1918 by default
- 401 → 1 s delay (brute force mitigation)
- `rate_limit_seconds` between requests
- 409 when countdown is already active
- `bind=0.0.0.0` — log warning, do not expose to internet

## UI

- English strings in `countdown.py` and `tray.py`
- Countdown: topmost, frameless, minimize all on show
- Foreground: `AllowSetForegroundWindow` + `SetForegroundWindow` (Win11)

## Autostart

- `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, value `PCSleepService`
- Disabled by default — user enables via tray menu

## Build

- `scripts/build_exe.cmd` or `scripts/build_exe.ps1` on Windows
- PyInstaller `--onefile --windowed`
