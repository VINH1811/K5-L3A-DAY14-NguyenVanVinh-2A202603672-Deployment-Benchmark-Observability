"""Config — 12-Factor: mọi cấu hình đọc từ biến môi trường."""
import os
from dataclasses import dataclass, field


def _env(name: str, default: str):
    return field(default_factory=lambda: os.getenv(name, default).strip())


def _env_int(name: str, default: int):
    return field(default_factory=lambda: int(os.getenv(name, str(default))))


def _env_float(name: str, default: float):
    return field(default_factory=lambda: float(os.getenv(name, str(default))))


@dataclass(frozen=True)
class Settings:
    port: int = _env_int("PORT", 8000)
    environment: str = _env("ENVIRONMENT", "development")
    log_level: str = _env("LOG_LEVEL", "INFO")
    # Không có giá trị mặc định: chưa đặt key thì /ask từ chối mọi request (fail closed).
    agent_api_key: str = _env("AGENT_API_KEY", "")
    redis_url: str = _env("REDIS_URL", "redis://localhost:6379/0")
    rate_limit_per_minute: int = _env_int("RATE_LIMIT_PER_MINUTE", 10)
    daily_budget_usd: float = _env_float("DAILY_BUDGET_USD", 1.0)


settings = Settings()
