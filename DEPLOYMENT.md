# Deployment Information

> **Trạng thái: CHƯA DEPLOY.** Cấu hình đã kiểm tra ở local; điền URL và kết quả sau khi deploy thật.

## Public URL

_(điền sau khi deploy)_

## Platform

Railway (`06-lab-complete/railway.toml`). Phương án thay thế: Render Blueprint (`06-lab-complete/render.yaml`).

## Test Commands

```bash
BASE=https://<url-cua-ban>
# AGENT_API_KEY: export trong terminal, không ghi vào file
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"     # 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"      # 200
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'   # 401
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'   # 200
```

Kết quả: _(điền 4 mã HTTP thật)_

## Environment Variables

Cần đặt trên nền tảng (không ghi giá trị vào đây):

- `AGENT_API_KEY` (secret)
- `REDIS_URL` (trỏ tới Redis trên nền tảng)
- `ENVIRONMENT=production`
- `RATE_LIMIT_PER_MINUTE=10`
- `DAILY_BUDGET_USD=1.0`
- `LOG_LEVEL=INFO`
- `PORT` do nền tảng tự cấp

## Screenshots

Cần chụp sau khi deploy: `screenshots/dashboard.png`, `screenshots/running.png`, `screenshots/test.png`.
