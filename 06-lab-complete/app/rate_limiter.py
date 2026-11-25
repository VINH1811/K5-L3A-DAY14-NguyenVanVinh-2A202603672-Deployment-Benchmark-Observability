"""Rate limiting: sliding window 60 giây cho mỗi API key, state nằm trong Redis."""
import hashlib
import math
import uuid

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

WINDOW_SECONDS = 60

# Lua chạy nguyên tử trong Redis: nhiều worker/instance gọi cùng lúc cũng không thể
# cùng đọc "còn chỗ" rồi cùng ghi. Dùng TIME của Redis nên không lệch đồng hồ giữa instance.
# Trả về 0 nếu được phép, ngược lại là số micro giây phải chờ.
_SLIDING_WINDOW = r.register_script("""
local t = redis.call("TIME")
local now = tonumber(t[1]) * 1000000 + tonumber(t[2])
local window = tonumber(ARGV[2]) * 1000000
redis.call("ZREMRANGEBYSCORE", KEYS[1], "-inf", string.format("%.0f", now - window))
if redis.call("ZCARD", KEYS[1]) >= tonumber(ARGV[1]) then
  local oldest = redis.call("ZRANGE", KEYS[1], 0, 0, "WITHSCORES")
  if not oldest[2] then return window end
  return math.max(1, tonumber(oldest[2]) + window - now)
end
redis.call("ZADD", KEYS[1], string.format("%.0f", now), ARGV[3])
redis.call("EXPIRE", KEYS[1], ARGV[2])
return 0
""")


def check_rate_limit(key: str) -> None:
    # Băm API key để không lưu secret dạng rõ trong Redis.
    key_id = hashlib.sha256(key.encode()).hexdigest()[:16]
    wait_us = int(_SLIDING_WINDOW(
        keys=[f"rate:{key_id}"],
        args=[settings.rate_limit_per_minute, WINDOW_SECONDS, uuid.uuid4().hex],
    ))
    if wait_us > 0:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(math.ceil(wait_us / 1_000_000))},
        )
