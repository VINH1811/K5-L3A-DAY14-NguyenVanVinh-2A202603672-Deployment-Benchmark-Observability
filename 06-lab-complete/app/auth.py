"""API Key authentication: header X-API-Key phải trùng AGENT_API_KEY, nếu không → 401."""
import secrets

from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from app.config import settings

# auto_error=False: tự trả 401, thay vì mã lỗi mặc định của FastAPI khi thiếu header.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    expected = settings.agent_api_key
    # compare_digest: thời gian so sánh không phụ thuộc số ký tự đúng (chống timing attack).
    if not expected or not api_key or not secrets.compare_digest(
        api_key.encode(), expected.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key
