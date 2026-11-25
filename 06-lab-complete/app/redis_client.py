"""Kết nối Redis dùng chung. from_url() chỉ tạo client, chưa mở kết nối tới Redis."""
import redis

from app.config import settings

r = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    # Timeout ngắn để /ready và /ask trả 503 nhanh khi Redis không phản hồi.
    socket_connect_timeout=2,
    socket_timeout=2,
)


def redis_healthy() -> bool:
    try:
        return bool(r.ping())
    except redis.RedisError:
        return False
