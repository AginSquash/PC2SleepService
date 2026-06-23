# Conventions

## Код

- `src/pc2sleep/` — пакет
- WinAPI только в `actions.py`, `autostart.py`, `single_instance.py`
- На non-Windows WinAPI — no-op / skip (для тестов на macOS)

## Безопасность

- Токен: `secrets.token_urlsafe(32)`, сравнение `hmac.compare_digest`
- Токен только в query (`?token=`) — по требованию; риск логов/истории браузера
- HTTP без TLS — только LAN
- `allowed_cidrs`: RFC1918 по умолчанию
- 401 → sleep 1s (brute force)
- `rate_limit_seconds` между запросами
- 409 если countdown уже активен
- `bind=0.0.0.0` — warn в лог, не пробрасывать в интернет

## UI

- Русский текст в `countdown.py`
- Countdown: topmost, frameless, minimize all on show
- Foreground: `AllowSetForegroundWindow` + `SetForegroundWindow` (Win11)

## Автозагрузка

- `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, value `PCSleepService`
- По умолчанию выкл — пользователь включает в трее

## Сборка

- `scripts/build_exe.ps1` на Windows
- PyInstaller `--onefile --windowed`
