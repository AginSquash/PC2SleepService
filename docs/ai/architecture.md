# Architecture

## Stack

- Python 3.11+, PySide6 (tray + countdown UI), stdlib `http.server`
- WinAPI: `powrprof.SetSuspendState`, `shutdown /s`, `Shell.Application.MinimizeAll` (comtypes)
- PyInstaller → single `.exe` (build on Windows only)

## Threads

```mermaid
flowchart LR
    Client --> HTTP["HTTP thread"]
    HTTP --> Emitter["ActionEmitter Signal"]
    Emitter --> Main["Qt main thread"]
    Main --> Countdown["CountdownDialog"]
    Countdown --> Actions["sleep/shutdown"]
```

- HTTP in daemon thread (`ThreadingHTTPServer`)
- UI only on main thread (Qt)
- `ActionEmitter` — thread-safe bridge HTTP → UI

## Data

- Config: `%APPDATA%/PCSleepService/config.json`
- Log: `%APPDATA%/PCSleepService/pc2sleep.log` (RotatingFileHandler)
- Single instance: mutex `Global\PCSleepService_v1`

## Startup

`python -m pc2sleep` → tray + HTTP server. No window until `/sleep` or `/shutdown` request arrives.
