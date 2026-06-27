"""FastAPI 应用."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sensehub.api.middleware import SecurityHeadersMiddleware
from sensehub.api.middleware_lan import LanAccessMiddleware
from sensehub.api.routes import admin, audit, auth, gamification, health, hub, license, models, perception, rules, security, sessions, tasks, tts, tunnel, user_settings, virtual_screen, voice, wallet
from sensehub.api.ws import router as ws_router
from sensehub.gateway.ws_agent import router as ws_agent_router
from sensehub.config.user_settings import ensure_default_save_path_ready
from sensehub.db.database import init_db
from sensehub.execution.kill_switch import reset as reset_kill_switch
from sensehub.feedback.hooks import setup_feedback_hooks
from sensehub.perception import init_perception
from sensehub.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_default_save_path_ready()
    init_perception()
    setup_feedback_hooks()
    reset_kill_switch()
    settings = get_settings()
    Path(settings.screenshots_dir).mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="灵枢 Agent", version="0.1.0", lifespan=lifespan)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LanAccessMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|[\w.-]+)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api")
    app.include_router(hub.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.include_router(user_settings.router, prefix="/api")
    app.include_router(license.router, prefix="/api")
    app.include_router(wallet.router, prefix="/api")
    app.include_router(gamification.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(models.router, prefix="/api")
    app.include_router(audit.router, prefix="/api")
    app.include_router(perception.router, prefix="/api")
    app.include_router(rules.router, prefix="/api")
    app.include_router(voice.router, prefix="/api")
    app.include_router(tts.router, prefix="/api")
    app.include_router(security.router, prefix="/api")
    app.include_router(virtual_screen.router, prefix="/api")
    app.include_router(tunnel.router, prefix="/api")
    app.include_router(ws_router)
    app.include_router(ws_agent_router)

    settings = get_settings()
    screenshots = settings.screenshots_dir
    if screenshots.exists():
        app.mount("/screenshots", StaticFiles(directory=str(screenshots)), name="screenshots")

    return app
