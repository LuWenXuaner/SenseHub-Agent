"""HTTP 安全与缓存响应头."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Frame-Options", "DENY")

        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json") and "charset" not in content_type.lower():
            response.headers["content-type"] = "application/json; charset=utf-8"
        elif content_type.startswith("text/") and "charset" not in content_type.lower():
            response.headers["content-type"] = f"{content_type.split(';')[0]}; charset=utf-8"

        return response
