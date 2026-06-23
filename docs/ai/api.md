# API

Base: `http://<host>:<port>` (default port `8765`)

Все эндпоинты — `GET`, токен в query: `?token=<token>`

## Endpoints

| Path | Token | Ответ | Действие |
|------|-------|-------|----------|
| `/ping` | да | 200 `ok` | healthcheck |
| `/sleep` | да | 202 `accepted` | countdown → сон |
| `/shutdown` | да | 202 `accepted` | countdown → выключение |

## Errors

| Code | Body | Причина |
|------|------|---------|
| 401 | `unauthorized` | неверный/нет токена (+ 1s delay) |
| 403 | `forbidden` | IP не в `allowed_cidrs` |
| 404 | `not_found` | неизвестный path |
| 409 | `countdown_active` / `rate_limited` | конфликт состояния |

## Пример

```
GET /sleep?token=YOUR_TOKEN
→ 202 accepted
```

После 202 на ПК: сворачивание окон, окно отсчёта 60 с, кнопка «Отмена».
