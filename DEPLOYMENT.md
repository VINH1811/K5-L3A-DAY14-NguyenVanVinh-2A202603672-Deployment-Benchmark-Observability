# Deployment Information

## Public URL

https://day14-agent-lwfp.onrender.com

## Platform

Render (gói Free, vùng Singapore), tạo từ Blueprint `06-lab-complete/render.yaml`: web service `day14-agent` và Key Value `day14-redis`.

Gói Free ngủ khi không có request, lần gọi đầu có thể mất khoảng một phút.

## Test Commands

```bash
BASE=https://day14-agent-lwfp.onrender.com
# AGENT_API_KEY: export trong terminal, không ghi vào file
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"     # 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"      # 200
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'   # 401
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'   # 200
```

Kết quả đã chạy ngày 25/11/2026: `/health` 200, `/ready` 200, `/ask` không có key 401, `/ask` có key: _(chờ điền)_

## Environment Variables Set

(không ghi giá trị secret vào đây)

- `AGENT_API_KEY` (Render tự sinh bằng `generateValue`)
- `REDIS_URL` (lấy từ `day14-redis` bằng `fromService`)
- `ENVIRONMENT=production`
- `RATE_LIMIT_PER_MINUTE=10`
- `DAILY_BUDGET_USD=1.0`
- `PORT` do nền tảng tự cấp

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
