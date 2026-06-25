# PC2Sleep Service

HTTP service for Windows 11: remotely put the PC to sleep or shut it down via a GET request from the local network. A countdown warning window (60 s) with a cancel button is shown before the action runs.

## Features

- `GET /sleep?token=...` — sleep after 60 seconds
- `GET /shutdown?token=...` — shutdown after 60 seconds
- `GET /ping?token=...` — availability check
- Warning window on top of all apps, minimizes open windows
- System tray icon, optional autostart
- Minimal background load (~0% CPU when idle)

## Requirements

- Windows 11 (or Windows 10)
- Python 3.11+ (for development / building)

## Installation (development)

```powershell
git clone <repo>
cd PC2SleepService
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m pc2sleep
```

On first launch, `%APPDATA%\PCSleepService\config.json` is created with a token. The token is shown once and copied to the clipboard.

## Building .exe (Windows only)

**Option 1 (easiest):** double-click:

```
scripts\build_exe.cmd
```

**Option 2:** from PowerShell in the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

> **Why does `.\scripts\build_exe.ps1` open in an editor?**  
> In cmd.exe and when double-clicking, Windows often associates `.ps1` with Notepad/editor instead of PowerShell. Use `build_exe.cmd` or the command above with `powershell -File`.

Output: `dist\PCSleepService.exe`

Copy the exe wherever you like and enable autostart from the tray menu if needed.

## Configuration

File: `%APPDATA%\PCSleepService\config.json`

```json
{
  "token": "<generated_token>",
  "port": 8765,
  "bind": "auto",
  "countdown_seconds": 60,
  "allowed_cidrs": ["127.0.0.0/8", "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"],
  "rate_limit_seconds": 5,
  "logging_enabled": true,
  "log_max_bytes": 1000000,
  "log_backup_count": 2,
  "log_ping_requests": false
}
```

| Parameter | Description |
|-----------|-------------|
| `token` | Secret for requests (min. 16 characters) |
| `port` | HTTP server port |
| `bind` | `auto` (default) — LAN IPs only, VPN-safe; `0.0.0.0` — all interfaces; or a specific IPv4 |
| `countdown_seconds` | Seconds before sleep/shutdown |
| `allowed_cidrs` | Allowed client subnets (RFC1918 by default) |
| `rate_limit_seconds` | Minimum interval between requests |
| `logging_enabled` | `false` disables all file logging |
| `log_max_bytes` | Max size per log file before rotation (default 1 MB) |
| `log_backup_count` | Number of rotated backup files kept (default 2) |
| `log_ping_requests` | `false` skips logging `/ping` requests (default) |

## Request examples

```bash
# Health check
curl "http://192.168.1.100:8765/ping?token=YOUR_TOKEN"

# Sleep
curl "http://192.168.1.100:8765/sleep?token=YOUR_TOKEN"

# Shutdown
curl "http://192.168.1.100:8765/shutdown?token=YOUR_TOKEN"
```

Responses: `200 ok`, `202 accepted`, `401 unauthorized`, `403 forbidden`, `409 conflict` (countdown already active or rate limited).

## VPN (AmneziaWG, WireGuard, etc.)

With an active VPN, `bind: "0.0.0.0"` often breaks LAN access: responses are routed through the VPN tunnel. **Use `bind: "auto"`** (default) — the server listens only on physical LAN adapters (AmneziaWG / Wintun / WireGuard interfaces are excluded).

If it still does not work:

1. In AmneziaWG, enable **Allow LAN / local network** (bypass LAN from the tunnel).
2. Set a fixed LAN IP explicitly, e.g. `"bind": "192.168.1.100"`.
3. Check Windows Firewall — allow inbound TCP on your port for **Private** networks.
4. Open tray menu → **Show token** — it lists the exact URLs to use.

Split-tunneling exclusions for the app process alone may not fix inbound LAN traffic; interface binding is what matters.

## Security

- **No TLS** — the token is visible on the network. Use only on a trusted LAN (WPA2/3 Wi‑Fi).
- **Token in query string** — may appear in proxy/browser logs. Do not expose the port to the internet.
- **Firewall** — allow inbound on the port from LAN only if needed.
- Token comparison uses `hmac.compare_digest` (timing-attack resistant).
- Invalid token → 1 s delay.
- Only private-network IPs are accepted by default.

## Logs

`%APPDATA%\PCSleepService\pc2sleep.log`

- Rotating files: default 1 MB per file, 2 backups (~3 MB total max)
- `/ping` requests are **not** logged by default (`log_ping_requests: false`)
- Set `"logging_enabled": false` in config to disable logging entirely (restart required)

## Tests (macOS / Linux / Windows)

```bash
pip install -e ".[dev]"
pytest
```

Tests cover config and HTTP logic without WinAPI.

## Project structure

```
src/pc2sleep/
  __main__.py      # entrypoint
  config.py        # configuration
  server.py        # HTTP
  actions.py       # sleep/shutdown/minimize (WinAPI)
  autostart.py     # startup registry
  single_instance.py
  ui/              # tray + countdown
```
