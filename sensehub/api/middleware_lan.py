"""局域网 IP 访问控制."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from sensehub.security.network import allow_lan_enabled, is_client_allowed


class LanAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)
        client = request.client.host if request.client else None
        if not is_client_allowed(client):
            detail = "仅允许本机访问" if not allow_lan_enabled() else f"IP {client} 不在白名单"
            return JSONResponse(status_code=403, content={"detail": detail})
        return await call_next(request)
