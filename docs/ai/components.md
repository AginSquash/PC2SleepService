# Components

| Module | Purpose |
|--------|---------|
| `__main__.py` | Entrypoint, logging, orchestration |
| `config.py` | Load/save JSON, token generation |
| `server.py` | HTTP endpoints, CIDR, rate limit, `ActionEmitter` |
| `actions.py` | `sleep_pc`, `shutdown_pc`, `minimize_all` |
| `autostart.py` | Registry Run key |
| `single_instance.py` | Named mutex |
| `ui/tray.py` | System tray menu |
| `ui/countdown.py` | 60s warning dialog |
| `ui/icon.py` | In-memory tray icon |

## WinAPI

- Sleep: `ctypes.windll.powrprof.SetSuspendState(0,0,0)`
- Shutdown: `subprocess shutdown /s /t 0`
- Minimize: `comtypes` → `Shell.Application.MinimizeAll()`
