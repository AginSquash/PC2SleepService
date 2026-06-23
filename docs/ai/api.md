# API

Base: `http://<host>:<port>` (default port `8765`)

All endpoints are `GET` with token in query: `?token=<token>`

## Endpoints

| Path | Token | Response | Action |
|------|-------|----------|--------|
| `/ping` | yes | 200 `ok` | healthcheck |
| `/sleep` | yes | 202 `accepted` | countdown → sleep |
| `/shutdown` | yes | 202 `accepted` | countdown → shutdown |

## Errors

| Code | Body | Reason |
|------|------|--------|
| 401 | `unauthorized` | invalid/missing token (+ 1s delay) |
| 403 | `forbidden` | IP not in `allowed_cidrs` |
| 404 | `not_found` | unknown path |
| 409 | `countdown_active` / `rate_limited` | state conflict |

## Example

```
GET /sleep?token=YOUR_TOKEN
→ 202 accepted
```

After 202 on the PC: windows minimized, 60 s countdown dialog, Cancel button.
