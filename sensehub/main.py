"""启动入口."""

from __future__ import annotations

import uvicorn

from sensehub.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "sensehub.api.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
