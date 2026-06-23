# Architecture

## Stack

- Python 3.11+, PySide6 (tray + countdown UI), stdlib `http.server`
- WinAPI: `powrprof.SetSuspendState`, `shutdown /s`, `Shell.Application.MinimizeAll` (comtypes)
- PyInstaller → single `.exe` (сборка только на Windows)

## Потоки

```mermaid
flowchart LR
    Client --> HTTP["HTTP thread"]
    HTTP --> Emitter["ActionEmitter Signal"]
    Emitter --> Main["Qt main thread"]
    Main --> Countdown["CountdownDialog"]
    Countdown --> Actions["sleep/shutdown"]
```

- HTTP в daemon-thread (`ThreadingHTTPServer`)
- UI только в main thread (Qt)
- `ActionEmitter` — thread-safe мост HTTP → UI

## Данные

- Конфиг: `%APPDATA%/PCSleepService/config.json`
- Лог: `%APPDATA%/PCSleepService/pc2sleep.log` (RotatingFileHandler)
- Single instance: mutex `Global\PCSleepService_v1`

## Запуск

`python -m pc2sleep` → tray + HTTP server. Окна нет до входящего запроса `/sleep` или `/shutdown`.
