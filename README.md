# PC2Sleep Service

HTTP-сервис для Windows 11: удалённый перевод ПК в сон или выключение по GET-запросу из локальной сети. Перед действием показывается окно с обратным отсчётом (60 с) и кнопкой отмены.

## Возможности

- `GET /sleep?token=...` — сон через 60 секунд
- `GET /shutdown?token=...` — выключение через 60 секунд
- `GET /ping?token=...` — проверка доступности
- Окно предупреждения поверх всех окон, сворачивание открытых программ
- Иконка в системном трее, автозагрузка (опционально)
- Минимальная нагрузка в фоне (~0% CPU в idle)

## Требования

- Windows 11 (или Windows 10)
- Python 3.11+ (для разработки / сборки)

## Установка (разработка)

```powershell
git clone <repo>
cd PC2SleepService
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m pc2sleep
```

При первом запуске создаётся `%APPDATA%\PCSleepService\config.json` с токеном. Токен показывается один раз и копируется в буфер.

## Сборка .exe (только на Windows)

```powershell
.\scripts\build_exe.ps1
```

Результат: `dist\PCSleepService.exe`

Скопируйте exe куда удобно, включите автозагрузку через меню трея.

## Конфигурация

Файл: `%APPDATA%\PCSleepService\config.json`

```json
{
  "token": "<сгенерированный_токен>",
  "port": 8765,
  "bind": "0.0.0.0",
  "countdown_seconds": 60,
  "allowed_cidrs": ["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"],
  "rate_limit_seconds": 5
}
```

| Параметр | Описание |
|----------|----------|
| `token` | Секрет для запросов (мин. 16 символов) |
| `port` | Порт HTTP-сервера |
| `bind` | `0.0.0.0` — все интерфейсы, `127.0.0.1` — только localhost |
| `countdown_seconds` | Секунды до сна/выключения |
| `allowed_cidrs` | Разрешённые подсети клиентов (RFC1918 по умолчанию) |
| `rate_limit_seconds` | Минимальный интервал между запросами |

## Примеры запросов

```bash
# Проверка
curl "http://192.168.1.100:8765/ping?token=YOUR_TOKEN"

# Сон
curl "http://192.168.1.100:8765/sleep?token=YOUR_TOKEN"

# Выключение
curl "http://192.168.1.100:8765/shutdown?token=YOUR_TOKEN"
```

Ответы: `200 ok`, `202 accepted`, `401 unauthorized`, `403 forbidden`, `409 conflict` (уже идёт отсчёт или rate limit).

## Безопасность

- **HTTP без TLS** — токен виден в сетевом трафике. Используйте только в доверенной LAN (WPA2/3 Wi‑Fi).
- **Токен в query string** — может попасть в логи прокси/браузера. Не открывайте порт в интернет.
- **Firewall** — при необходимости разрешите входящие на порт только из LAN.
- Токен сравнивается через `hmac.compare_digest` (защита от timing-атак).
- Неверный токен → задержка 1 с.
- По умолчанию принимаются только IP из частных подсетей.

## Логи

`%APPDATA%\PCSleepService\pc2sleep.log` (ротация до 3 файлов по 1 МБ).

## Тесты (macOS / Linux / Windows)

```bash
pip install -e ".[dev]"
pytest
```

Тесты покрывают конфиг и HTTP-логику без WinAPI.

## Структура

```
src/pc2sleep/
  __main__.py      # entrypoint
  config.py        # конфиг
  server.py        # HTTP
  actions.py       # sleep/shutdown/minimize (WinAPI)
  autostart.py     # реестр автозагрузки
  single_instance.py
  ui/              # tray + countdown
```
