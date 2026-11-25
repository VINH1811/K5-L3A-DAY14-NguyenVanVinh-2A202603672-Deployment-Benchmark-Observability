# Benchmark & Observability Report — Day 14

**Họ tên:** Nguyễn Văn Vinh
**MSSV:** 2A202603672
**Ngày chạy:** 25/11/2026
**Môi trường:** Windows 11 + WSL2 Ubuntu 22.04, Intel Core i9-12900H (WSL thấy 20 CPU / 7,7 GB RAM), Docker 29.1.2, Python 3.11.18. Mỗi container agent bị giới hạn 0,5 CPU / 256 MB.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | < 500 ms | p50 bình thường ≈ 200 ms; 500 ms còn khoảng dư cho jitter nhưng vẫn phát hiện khi hơn 5% request rơi vào nhóm chậm ~1,7 s |
| Error rate `/ask` | < 2 % | LLM mock lỗi ~1%; cho phép gấp đôi để bớt báo nhầm |
| Accuracy trên golden dataset | ≥ 85 % | v2 ban đầu đạt 91,3%; 85% cho sai tối đa 3/23 câu |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

300 request mỗi mức. Nguồn: `reports/load_v2_c*.json`.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.2 | 199.9 | 225.8 | 1707.2 | 3.00% | FAIL (error rate) |
| 10 | 37.61 | 193.1 | 223.3 | 1708.0 | 1.33% | PASS |
| 50 | 109.5 | 203.9 | 299.0 | 1691.6 | 2.00% | PASS |
| 100 | 44.37 | 755.4 | 4388.5 | 4768.6 | 0.33% | FAIL (p95) |

Cột SLO lấy từ kết quả script (p95 ≤ 500 ms, error rate ≤ 2%).

**Nhận xét:** RPS không tăng tuyến tính trên toàn dải.

- Từ 1 lên 10, RPS tăng ~9 lần: phần lớn thời gian là chờ LLM (I/O, `async`) nên request chạy chồng được.
- Từ 10 lên 50, RPS chỉ tăng ~2,9 lần. Với 300 request, vài request chậm 1,7 s cũng kéo dài đáng kể tổng thời gian đo.
- Ở 100, RPS giảm còn 44 và p50 lên 755 ms: hệ thống bão hoà, request phải xếp hàng. Agent và công cụ bắn tải chạy chung một máy, mỗi bên một event loop, nên từ số liệu này chưa tách được phần nào do agent, phần nào do client.
- Error rate dao động quanh mức 1% lỗi ngẫu nhiên của mock. Mức 1 có 9 lỗi nhưng mức 100 chỉ có 1, nên lỗi không tăng theo tải; 300 request là mẫu nhỏ.

### 2.2 Tail latency

300 request, concurrency 20. Nguồn: `reports/load_v2_slow_*.json`.

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 191.1 | 219.9 | 236.7 |
| 0.03 (mặc định) | 229.3 | 254.0 | 1686.8 |
| 0.1 | 340.9 | 1700.8 | 1715.6 |

**Nhận xét:** p99 nhạy nhất. 3% request chậm đã đưa p99 từ 237 lên 1687 ms (×7), trong khi avg chỉ tăng 38 ms và p95 tăng 34 ms. Khi tỉ lệ chậm vượt 5%, p95 cũng nhảy lên 1701 ms. Average trộn hai nhóm: 341 ms không mô tả đúng trải nghiệm của ai, vì người dùng hoặc chờ ~200 ms hoặc chờ ~1,7 s. Vì vậy SLO nên đặt theo percentile.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

Eval chạy với `MOCK_ERROR_RATE=0` để kết quả không phụ thuộc lỗi ngẫu nhiên. Nguồn: `reports/eval_*.json`.

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100% (23/23) |
| Avg tokens / câu | 56.3 | 109.0 | 113.7 |
| Tổng cost (USD) | 0.000394 | 0.000759 | 0.00079 |
| Cost / câu đúng (USD) | 0.00039375 | 0.00003616 | 0.00003436 |
| Quality gate | FAIL (≥ 80%) | PASS (≥ 80%) | PASS (≥ 100%, không regression) |

**Những câu v2 trả lời sai ban đầu và cách sửa:**

| ID | Keyword bị thiếu | Đã sửa gì |
|---|---|---|
| `scaling-03` | cpu, memory, custom metrics | Thêm tài liệu Kubernetes HPA vào `KNOWLEDGE_BASE` |
| `security-02` | token, hết hạn, chữ ký | Thêm tài liệu so sánh JWT và API key |

**Trade-off:** v2 dùng gần gấp đôi token và tổng cost; p95 trong eval tăng 36 ms (194,3 → 230,4) vì có thêm retrieval và prompt dài hơn. Đổi lại accuracy tăng 87 điểm %, cost trên mỗi câu đúng rẻ hơn ~11 lần. Nếu nhìn "cost / câu" thì v1 trông rẻ hơn, nhưng phần lớn tiền của v1 mua câu trả lời sai. 23 câu là mẫu nhỏ nên latency ở đây chỉ để tham khảo.

**Quality gate trong CI:** [`.github/workflows/eval.yml`](.github/workflows/eval.yml) chạy eval trên mỗi pull request. `run_eval.py` trả exit code 1 khi accuracy dưới ngưỡng (hoặc có regression nếu truyền `--baseline`), bước đó fail và job đỏ. Đặt job `eval` là required check trong branch protection thì PR không merge được. Đã kiểm chứng exit code ở local: v1 so với baseline v2 trả 1 (20 câu regression); v2 sau khi sửa trả 0. Workflow chưa chạy trên GitHub.

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [x] [Dashboard Grafana khi đang có tải](screenshots/grafana-dashboard.png)
- [x] [Trace chậm trong Jaeger](screenshots/jaeger-slow-trace.png)
- [x] [Trace lỗi trong Jaeger, có event `exception`](screenshots/jaeger-error-trace.png)
- [x] [Trang Alerts của Prometheus, 2 alert đang firing](screenshots/prometheus-alert-firing.png)

**Exercise 7.1:** Counter `http_requests_total`, Gauge `agent_in_flight_requests`, Histogram `http_request_duration_seconds`. Nếu label dùng URL thật, mỗi URL lạ do bot quét tạo thêm time series (histogram còn nhân với số bucket), cardinality bùng nổ và Prometheus hết RAM. Dùng `route.path` thì URL lạ gộp hết vào `unmatched`. Metric `agent_question_length_chars` đã thêm trong `develop/app.py`.

**Exercise 7.4** (tải 30 user, v2):

1. p95 ≈ 294 ms, avg ≈ 233 ms; ảnh Grafana cho thấy p99 ≈ 1,8 s. p95 và avg gần nhau nhưng p99 tách hẳn: khoảng 3% request là tail latency mà avg che mất.
2. Nginx chia đều: hai instance nhận 10,09 và 10,14 req/s.
3. Input 1541 token/s, output 803 token/s. Prompt gồm system prompt + tài liệu retrieval + câu hỏi, còn câu trả lời ngắn.
4. `curl http://localhost:8080/metrics` trả 404 từ Nginx. Metrics lộ thông tin nội bộ (traffic, model, chi phí) nên chỉ Prometheus trong mạng Docker được scrape thẳng agent.

### 4.2 Thí nghiệm "phá hệ thống"

Điều kiện: 2 instance, Locust 15 user. Không dùng 30 user vì tải đó đã làm `LLMCostBurnRateHigh` firing sẵn (cost đo được $4,24/giờ, số này còn lẫn tải 100 user của bài scaling trong cửa sổ 5 phút), thí nghiệm C sẽ mất ý nghĩa. Baseline 15 user: error 0,5%, p95 295 ms, cost $1,83/giờ, không alert nào. Thời gian lấy từ API `/api/v1/alerts`, hỏi mỗi 2 giây, tính từ khi lệnh đổi cấu hình chạy xong.

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | 92 s (pending ở 32 s) | Error rate: 24,3% |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | 137 s (pending ở 18 s) | Latency: p95 1,92 s, avg 0,63 s |
| C | `LLM_MODEL=mock-llm-large` | `LLMCostBurnRateHigh` | 149 s (pending ở 30 s) | Cost burn rate: $9,06/giờ lúc firing |
| D | `docker pause` 1 instance | `AgentInstanceDown` | 44 s (pending ở 14 s) | Instances up; req/s theo instance (1,5 so với 6,2) |
| E | `AGENT_VERSION=v1` | Không có (theo dõi 240 s) | — | Tokens/s giảm còn 369 input / 200 output; bảng version |

Ảnh hai alert cùng firing chụp ở lần chạy riêng, đặt đồng thời `MOCK_ERROR_RATE=0.2` và `MOCK_SLOW_RATE=0.3` (cả hai firing sau 145 s).

`AgentInstanceDown` có pending ngắn mỗi lần tạo lại container nhưng không firing, nhờ `for: 30s`.

**Thí nghiệm E không làm alert nào firing. Phát hiện bằng cách nào?** Sau khi đổi sang v1, dashboard còn *đẹp hơn*: p95 giảm còn 199 ms, cost còn $0,66/giờ, trong khi eval của v1 chỉ đạt 4,3%. Metric hạ tầng chỉ biết request có thành công và nhanh hay không, không biết nội dung đúng hay sai. Cần: (1) eval golden dataset làm quality gate trước deploy; (2) eval định kỳ trên mẫu traffic thật; (3) tín hiệu gián tiếp như feedback người dùng, retrieval hit ratio, tokens/câu; (4) alert khi `agent_info` đổi version ngoài kế hoạch.

**Vì sao lỗi ở thí nghiệm D không hiện trên Error rate?** Log Nginx trong khoảng 15:47–15:48 có 14 dòng 504, nhưng error rate do agent tự báo chỉ 1,0%. Request tới instance bị pause hết hạn ở Nginx, agent chưa xử lý xong nên không đếm. Metric chỉ phản ánh điều chính service đó thấy; cần thêm giám sát ở load balancer hoặc synthetic check từ ngoài. (Cùng khoảng log đó còn có 502, trùng lúc container được tạo lại cho thí nghiệm E, nên không tính cho D.)

### 4.3 Debug bằng trace

- `trace_id`: `cb7f600909bb0c176cb909d6b053a98c`
- Tổng thời gian: 1751.5 ms
- Span chiếm nhiều thời gian nhất: `chat mock-llm-small` (1673.9 ms, 95.6%); `agent.retrieve_context` chỉ 17.6 ms
- Dòng log tương ứng (grep theo `trace_id`):

```json
{"ts": "2026-11-25T08:26:58.499519+00:00", "level": "INFO", "service": "observable-agent", "instance": "066969daba4b", "event": "llm_call", "trace_id": "cb7f600909bb0c176cb909d6b053a98c", "span_id": "578c9aad14f8c3de", "request_id": "fb6151829310", "model": "mock-llm-small", "agent_version": "v2", "input_tokens": 95, "output_tokens": 55, "cost_usd": 4.7e-05, "llm_ms": 1672.7}
{"ts": "2026-11-25T08:26:58.500286+00:00", "level": "INFO", "service": "observable-agent", "instance": "066969daba4b", "event": "http_request", "trace_id": "cb7f600909bb0c176cb909d6b053a98c", "span_id": "578c9aad14f8c3de", "request_id": "fb6151829310", "method": "POST", "route": "/ask", "status": 200, "ms": 1750.4}
```

Trace lỗi `9f0a6d7469052211cfc67bef7132ab21` (118,7 ms, HTTP 503, event `exception` trong span `chat mock-llm-small`):

```json
{"ts": "2026-11-25T08:31:37.822976+00:00", "level": "INFO", "service": "observable-agent", "instance": "066969daba4b", "event": "llm_error", "trace_id": "9f0a6d7469052211cfc67bef7132ab21", "span_id": "5c790ed0f2995a22", "request_id": "4cc23e960ff1", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

Dòng `POST /ask` trong `benchmark-results/scale_*_stats.csv`:

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 63.67 | 200 | 510 | 1700 | 90 / 6995 (1.29%) |
| 3 | 64.75 | 200 | 230 | 1700 | 75 / 7117 (1.05%) |

**Giải thích kết quả:**

- RPS gần như bằng nhau vì 100 user đều nghỉ 0,5–2 s giữa các lần gọi: tải do client quyết định, một instance đã theo kịp.
- p95 giảm từ 510 xuống 230 ms. Một instance chỉ có 0,5 CPU nên nhiều khả năng có lúc xếp hàng; max của `/health` (không gọi LLM) giảm từ 295 xuống 63 ms cũng phù hợp với cách giải thích này.
- p50 và p99 không đổi: p50 là latency LLM bình thường, p99 là ~3% request LLM chậm. Scale agent không làm LLM nhanh hơn, nút thắt của hai mức này nằm ở LLM.

**Lưu ý về cách đo:** lệnh `docker compose run --rm locust` trong đề khởi động cả service phụ thuộc và đưa agent về `replicas: 2`, nên lần đo đầu thành 2 instance cho cả hai lượt. Đã thêm `--no-deps`, đo lại và kiểm tra `docker compose ps` sau mỗi lượt: đúng 1 và 3 instance. CSV nộp là của lần đo lại.

---

## 6. Kết luận

- 3 điều học được về benchmark & observability:
  1. Average che tail latency: 3% request chậm đẩy p99 lên 7 lần mà avg chỉ nhích 38 ms.
  2. Hệ thống "xanh" chưa chắc đúng: đổi sang v1 làm latency và cost đẹp hơn trong khi accuracy chỉ còn 4,3%.
  3. Phải kiểm tra điều kiện đo trước khi tin số liệu: benchmark scaling lần đầu hoá ra so 2 instance với 2 instance.
- Nếu đưa lên production sẽ thêm: error rate và latency đo ở Nginx, synthetic check từ ngoài, accuracy từ eval định kỳ, alert retrieval hit ratio, alert theo burn rate của error budget, số liệu Redis và số lần bị 402/429.
