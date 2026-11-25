# Day 14 Lab - Mission Answers

Chạy ngày 25/11/2026 trên WSL2 Ubuntu 22.04, Python 3.11.18, Docker 29.1.2.

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

Trong `01-localhost-vs-production/develop/app.py`:

1. Hardcode `OPENAI_API_KEY` và `DATABASE_URL` có mật khẩu: push lên Git là lộ, muốn đổi key phải sửa code.
2. In key ra log: `print(f"[DEBUG] Using key: ...")`. Ai đọc được log là có key.
3. Config cố định (`DEBUG = True`, `MAX_TOKENS = 500`), không tách theo môi trường.
4. Dùng `print()` thay cho logging có level và cấu trúc.
5. Không có `/health`, `/ready`: platform không biết khi nào cần restart hay ngừng gửi traffic.
6. `host="localhost"`: trong container, bên ngoài không gọi vào được.
7. Cứng `port=8000`, trong khi Railway/Render cấp cổng qua `PORT`.
8. `reload=True` cố định: chạy thêm process theo dõi file, không dành cho production.
9. Không có lifespan hay bước dọn dẹp khi tắt.

### Exercise 1.2: Chạy bản develop

```text
POST /ask?question=Hello -> 200 {"answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
GET  /health             -> 404 {"detail":"Not Found"}
POST /ask với JSON body  -> 422 (bản này nhận question qua query)
log: [DEBUG] Using key: sk-***   (log thật in đầy đủ key; đã che khi dán)
```

Chạy được nhưng chưa production-ready: lộ secret, không có health check, chỉ nghe ở localhost.

### Exercise 1.3: Comparison table

Kết quả bản production: `/health` 200, `/ready` 200, `POST /ask` với JSON 200.

| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config / secret | Hardcode trong `app.py` | `config.py` đọc env | Cùng một image chạy được ở dev/staging/prod; đổi key không cần build lại; secret không vào Git |
| Health check | Không có (404) | `/health`, `/ready` | Platform biết khi nào restart (liveness) và khi nào ngừng gửi traffic (readiness) |
| Logging | `print()`, in cả key | `logging` với format JSON, không ghi key | Lọc và tìm kiếm tự động được; log không thành nơi lộ secret |
| Shutdown | Không dọn dẹp | Có lifespan và handler SIGTERM | Khi deploy bản mới, request đang chạy không bị cắt ngang |
| Host / port | `localhost:8000` cố định | `0.0.0.0` và `PORT` từ env | Container nhận được kết nối từ ngoài, đúng cổng platform cấp |
| Debug reload | Luôn bật | Chỉ khi `DEBUG=true` | Giảm rủi ro và tài nguyên ở production |

Nhận xét khi chạy thật: bản production **không in dòng log JSON nào** ở local. `config.py` gọi `logging.warning(...)` trước nên root logger đã có handler, `logging.basicConfig(...)` trong `app.py` không còn tác dụng. Ngoài ra format JSON ghép chuỗi sẽ hỏng khi message chứa dấu `"`. Vì vậy Part 6 dùng `logging.Formatter` riêng với `json.dumps`.

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image:** `python:3.11` (bản đầy đủ).
2. **Working directory:** `/app`.
3. **Vì sao COPY requirements.txt trước?** Docker cache theo layer. Chỉ sửa code thì layer `pip install` vẫn dùng lại được; nếu `COPY . .` trước, sửa một dòng code cũng phải cài lại toàn bộ.
4. **CMD vs ENTRYPOINT:** `CMD` là lệnh/tham số mặc định, bị thay khi thêm lệnh sau `docker run image`. `ENTRYPOINT` là chương trình chính, tham số của `docker run` được nối vào; muốn thay phải dùng `--entrypoint`. Có cả hai thì `CMD` là tham số mặc định của `ENTRYPOINT`.

### Exercise 2.2: Build và run

```text
POST /ask?question=What is Docker -> 200 {"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
GET  /health                      -> 200 {"status":"ok","uptime_seconds":3.9,"container":true}
```

### Exercise 2.3: Image size comparison

Đo bằng `docker images` (Docker 29 hiện riêng dung lượng trên đĩa và dung lượng nội dung nén):

| Image | Trên đĩa | Nội dung nén |
|---|---:|---:|
| Develop | 1.67 GB | 426 MB |
| Production | 240 MB | 57.4 MB |
| **Difference** | **−85.6%** | **−86.5%** |

- **Stage 1 (builder):** cài gcc, libpq-dev rồi `pip install --user`.
- **Stage 2 (runtime):** bắt đầu lại từ `python:3.11-slim`, chỉ copy package đã cài và code, chạy bằng user non-root, có HEALTHCHECK.
- **Vì sao nhỏ hơn:** base slim thay cho bản đầy đủ, và compiler của builder không vào image cuối.

### Exercise 2.4: Docker Compose stack

```text
Client ──:80──▶ Nginx ──:8000──▶ Agent (FastAPI) ──┬──:6379──▶ Redis  (cache/session)
                                                   └──:6333──▶ Qdrant (vector DB)
chỉ Nginx mở cổng ra ngoài; cả 4 service cùng mạng "internal"
```

Service gọi nhau bằng tên qua DNS nội bộ của Docker (`redis:6379`, `qdrant:6333`). Agent chờ Redis và Qdrant healthy mới khởi động.

```text
agent healthy · redis healthy · qdrant healthy · nginx up (80, 443)
GET  http://localhost/health -> 200 {"status":"ok","uptime_seconds":23.9,"version":"2.0.0",...}
POST http://localhost/ask    -> 200 {"answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
```

## Part 3: Cloud Deployment

### Exercise 3.1 / 3.2: Deployment

- Nền tảng chính: Render (Exercise 3.2), deploy agent Part 6
- URL: https://day14-agent-lwfp.onrender.com
- Screenshot: [dashboard](screenshots/dashboard.png), [running](screenshots/running.png), [test](screenshots/test.png)

### So sánh `railway.toml` và `render.yaml`

| | `railway.toml` | `render.yaml` |
|---|---|---|
| Phạm vi | Cách build và chạy **một** service | Blueprint cho **cả hạ tầng**: web service và Redis |
| Build | `builder = "DOCKERFILE"` | `runtime: docker`, `rootDir`, `dockerContext` |
| Health check | `healthcheckPath` | `healthCheckPath` |
| Biến môi trường | Đặt ngoài file (dashboard/CLI) | Khai báo trong file: `generateValue`, `fromService`, `sync: false` |
| Redis | Tạo riêng trên Railway rồi nối `REDIS_URL` | Khai báo service `keyvalue`, nối bằng `fromService` |
| Restart | `restartPolicyType` trong file | Không khai báo, do platform xử lý |

Khác nhau vì Railway để hạ tầng và biến trên nền tảng, file chỉ mô tả cách deploy; Render theo hướng Infrastructure as Code, một file dựng lại được toàn bộ môi trường. Cả hai đều không ghi giá trị secret vào file.

### Exercise 3.3: Pipeline Cloud Run

Theo `cloudbuild.yaml`, pipeline có 4 bước nối tiếp bằng `waitFor`: **test** (pytest) → **build** image, dùng lại cache từ bản `latest` → **push** lên registry → **deploy** Cloud Run.
Image gắn tag `$COMMIT_SHA` nên biết chính xác commit nào đang chạy và rollback được. Test fail thì các bước sau không chạy.
`service.yaml` khai báo service: 1–10 instance, tối đa 80 request đồng thời mỗi instance, 1 CPU / 512 Mi, timeout 60 s, liveness `/health` và startup probe `/ready`.
`minScale: 1` tránh cold start, đổi lại luôn tốn tiền một instance. Secret lấy từ Secret Manager, không nằm trong file.

## Part 4: API Security

### Exercise 4.1: API key

- Key được kiểm tra trong `verify_api_key`, gắn vào `/ask` bằng `Depends`.
- Thiếu key → 401; sai key → 403 (bản mẫu). Part 6 trả 401 cho cả hai theo yêu cầu.
- Rotate: đổi `AGENT_API_KEY` rồi restart. Muốn không gián đoạn thì chấp nhận đồng thời key cũ và mới trong thời gian chuyển tiếp.

```text
# Không có key
HTTP/1.1 401 Unauthorized
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

# Sai key
HTTP/1.1 403 Forbidden
{"detail":"Invalid API key."}

# Đúng key
HTTP/1.1 200 OK
{"question":"Hello","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

### Exercise 4.2: JWT

`POST /auth/token` kiểm tra username/password, trả JWT ký HS256 chứa `sub`, `role`, `iat`, `exp` (60 phút). Các request sau gửi `Authorization: Bearer <token>`; server kiểm chữ ký và hạn, không cần tra database.

```text
# Không có token
HTTP/1.1 401 Unauthorized
www-authenticate: Bearer
{"detail":"Authentication required. Include: Authorization: Bearer <token>"}
```

### Exercise 4.3: Rate limiting

- Thuật toán: sliding window, lưu timestamp trong `deque` cho từng user.
- Giới hạn: 10 req/phút cho user, 100 req/phút cho admin.
- Admin không bỏ qua hẳn giới hạn mà dùng limiter riêng theo `role`.
- Hạn chế: lưu trong RAM nên mất khi restart và mỗi instance đếm riêng.

```text
Vòng lặp 20 request: request 1–10 -> 200, request 11–20 -> 429

HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
retry-after: 59
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

### Exercise 4.4: Cost guard implementation

Bản `check_budget(user_id, estimated_cost)` theo đề ($10/tháng/user), viết bằng Lua để kiểm tra và cộng trong một thao tác nguyên tử:

```python
_SCRIPT = r.register_script("""
local spent = tonumber(redis.call("GET", KEYS[1]) or "0")
if spent + tonumber(ARGV[1]) > tonumber(ARGV[2]) then return 0 end
redis.call("INCRBYFLOAT", KEYS[1], ARGV[1])
redis.call("EXPIRE", KEYS[1], ARGV[3])
return 1
""")

def check_budget(user_id: str, estimated_cost: float) -> bool:
    key = f"budget:{user_id}:{datetime.now(timezone.utc):%Y-%m}"
    return bool(_SCRIPT(keys=[key], args=[estimated_cost, 10, 32 * 24 * 3600]))
```

- Key chứa tháng nên tự reset đầu tháng; TTL 32 ngày để Redis tự dọn.
- Nếu GET rồi mới INCR bằng hai lệnh rời, hai request cùng lúc có thể cùng thấy "còn tiền" và cùng vượt ngân sách.
- Đoạn trên viết cho câu hỏi này, chưa chạy riêng. Bản đã chạy và được script kiểm tra nằm ở `06-lab-complete/app/cost_guard.py`: cộng chi phí sau khi gọi LLM, ngân sách chung theo ngày, vượt thì 402. Vì chi phí ghi sau, các request đang chạy đồng thời có thể vượt một chút.

Rate limit giới hạn **tốc độ**, cost guard giới hạn **tổng tiền**. Gọi chậm nhưng đều vẫn có thể hết tiền; ngân sách còn nhiều vẫn có thể bị bắn dồn làm sập. Vì vậy cần cả hai.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

```text
GET /health -> 200 {"status":"ok","uptime_seconds":0.7,...,"checks":{"memory":{"status":"ok","used_percent":12.1}}}
GET /ready  -> 200 {"ready":true,"in_flight_requests":1}
```

- Liveness (`/health`): process còn sống không. Fail thì **restart**.
- Readiness (`/ready`): nhận traffic được không. Fail thì **ngừng gửi traffic**, không restart.
- Nếu `/health` phụ thuộc Redis, Redis chết sẽ làm mọi instance bị restart liên tục dù restart không sửa được gì.

### Exercise 5.2: Graceful shutdown

Gửi 2 request đồng thời, SIGTERM sau 0,5 giây:

```text
request one -> 200 sau 3.06s
request two -> 000 (kết nối đóng, không có response) sau 3.06s
log: Shutting down → POST /ask?question=one 200 OK → Waiting for application shutdown → Graceful shutdown initiated → Shutdown complete
```

Request đang xử lý hoàn thành và process thoát sạch, nhưng request thứ hai **bị mất**, khác kết quả mong đợi trong README. Giải thích: `/ask` khai báo `async def` nhưng gọi `ask()` có `time.sleep`, chặn event loop. Trong 3 giây đó server không đọc được request thứ hai; khi chạy tiếp thì đã ở trạng thái shutdown nên đóng kết nối. Part 6 dùng `def ask(...)`, FastAPI chạy nó trong thread pool nên event loop không bị chặn.

### Exercise 5.3: Stateless design

`05-scaling-reliability/production/app.py` lưu session vào Redis (`setex`, TTL 1 giờ) thay vì dict. State trong RAM hỏng khi scale vì mỗi instance có bộ nhớ riêng: request sau rơi vào instance khác là mất lịch sử, và restart là mất hết.

Hạn chế của bản mẫu: `append_to_history` đọc, sửa rồi ghi cả JSON nên hai request đồng thời cùng session có thể ghi đè nhau (`RPUSH` + `LTRIM` an toàn hơn). Nếu Redis chưa sẵn sàng lúc khởi động, app âm thầm chuyển sang RAM.

### Exercise 5.4: Load balancing

3 agent, Nginx cổng 8080, Redis. 10 request liên tiếp lần lượt vào `e0f95e → ef711e → 38455f → e0f95e → ...`: Nginx chia round-robin đều.

Thử `docker kill` một instance rồi gửi 6 request: 4 request trả 200 từ hai instance còn lại, **2 request treo tới khi client hết hạn 20 giây**. Lịch sử session vẫn đọc được từ Redis. Nguyên nhân khả dĩ: Nginx của bản mẫu không đặt `proxy_connect_timeout` (mặc định 60 s) nên chờ rất lâu khi kết nối tới địa chỉ container đã mất, rồi mới thử instance khác. Hướng khắc phục (chưa thử): giảm `proxy_connect_timeout` xuống 1–2 s, thêm `max_fails`/`fail_timeout` và `resolve` để Nginx cập nhật DNS.

### Exercise 5.5: Test stateless

```text
Request 1: [instance-e0f95e]
Request 2: [instance-ef711e]
Request 3: [instance-38455f]
Request 4: [instance-e0f95e]
Request 5: [instance-ef711e]
Total requests: 5
Instances used: {'instance-e0f95e', 'instance-ef711e', 'instance-38455f'}
Total messages: 10
✅ Session history preserved across all instances via Redis!
```

5 câu hỏi do 3 instance trả lời nhưng lịch sử vẫn đủ 10 message (5 user + 5 assistant), vì cả ba cùng đọc/ghi một Redis.

## Part 6: Final Project

Output `python check_production_ready.py` (đầy đủ, có Docker, chạy trong WSL2):

```text
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 43/43 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

Kiểm tra thêm bằng `docker compose` (agent + Redis):

```text
GET  /health                     -> 200 {"status":"ok"}
GET  /ready                      -> 200 {"status":"ready"}
POST /ask thiếu key / sai key    -> 401 {"detail":"Invalid or missing API key"}
POST /ask đúng key               -> 200
POST /ask thiếu field, JSON hỏng -> 422, không lộ stack trace
20 request đồng thời (giới hạn 10, đã dùng 1) -> 9 × 200, 11 × 429; retry-after: 60
Dừng Redis: /health 200 · /ready 503 · /ask 503 (mất ~4 s)
```

Cách ráp: `/ask` đi qua API key (401) → rate limit (429) → ngân sách (402) → LLM → ghi chi phí. Rate limit là sliding window trong Redis sorted set, chạy bằng Lua nên vẫn đúng khi 2 worker xử lý đồng thời. Redis lỗi thì `/ask` trả 503 thay vì bỏ qua giới hạn.

Part 7: xem `BENCHMARK_REPORT.md`.
