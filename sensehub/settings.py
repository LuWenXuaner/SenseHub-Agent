"""配置加载：local.env + paths.yaml + models.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    sensehub_root: str = Field(default=str(ROOT), alias="SENSEHUB_ROOT")
    python_path: str = Field(default="", alias="PYTHON_PATH")
    data_root: str = Field(default="", alias="DATA_ROOT")
    models_root: str = Field(default="", alias="MODELS_ROOT")
    sqlite_path: str = Field(default="", alias="SQLITE_PATH")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8765, alias="API_PORT")
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    admin_password: str = Field(default="sensehub", alias="ADMIN_PASSWORD")
    license_tier: str = Field(default="lite", alias="LICENSE_TIER")
    edge_path: str = Field(default="", alias="EDGE_PATH")
    camera_index: int = Field(default=0, alias="CAMERA_INDEX")
    mic_device_name: str = Field(default="", alias="MIC_DEVICE_NAME")
    use_cuda: bool = Field(default=True, alias="USE_CUDA")
    ffmpeg_path: str = Field(default="", alias="FFMPEG_PATH")
    tts_enabled: bool = Field(default=True, alias="TTS_ENABLED")
    tts_voice: str = Field(default="zh-CN-XiaoxiaoNeural", alias="TTS_VOICE")

    siliconflow_api_key: str = Field(default="", alias="SILICONFLOW_API_KEY")
    siliconflow_base_url: str = Field(
        default="https://api.siliconflow.cn/v1", alias="SILICONFLOW_BASE_URL"
    )
    volcengine_api_key: str = Field(default="", alias="VOLCENGINE_API_KEY")
    volcengine_base_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3", alias="VOLCENGINE_BASE_URL"
    )

    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="", alias="SMTP_FROM")
    email_dev_expose_code: bool = Field(default=False, alias="EMAIL_DEV_EXPOSE_CODE")

    oauth_frontend_url: str = Field(default="http://127.0.0.1:5173", alias="OAUTH_FRONTEND_URL")
    github_oauth_client_id: str = Field(default="", alias="GITHUB_OAUTH_CLIENT_ID")
    github_oauth_client_secret: str = Field(default="", alias="GITHUB_OAUTH_CLIENT_SECRET")
    qq_oauth_app_id: str = Field(default="", alias="QQ_OAUTH_APP_ID")
    qq_oauth_app_key: str = Field(default="", alias="QQ_OAUTH_APP_KEY")
    wechat_oauth_app_id: str = Field(default="", alias="WECHAT_OAUTH_APP_ID")
    wechat_oauth_app_secret: str = Field(default="", alias="WECHAT_OAUTH_APP_SECRET")

    @classmethod
    def load(cls) -> Settings:
        env_file = CONFIG_DIR / "local.env"
        dotenv = _load_dotenv(env_file)
        return cls(**dotenv)

    @property
    def paths(self) -> dict[str, Any]:
        return _load_yaml(CONFIG_DIR / "paths.yaml")

    @property
    def models_config(self) -> dict[str, Any]:
        path = CONFIG_DIR / "models.yaml"
        if path.exists():
            return _load_yaml(path)
        return _load_yaml(CONFIG_DIR / "models.yaml.example")

    @property
    def policies(self) -> dict[str, Any]:
        path = CONFIG_DIR / "policies.yaml"
        if path.exists():
            return _load_yaml(path)
        return _load_yaml(CONFIG_DIR / "policies.yaml.example")

    @property
    def screenshots_dir(self) -> Path:
        p = self.paths.get("data", {}).get("screenshots")
        if p:
            return Path(p)
        return Path(self.data_root) / "screenshots"


@lru_cache
def get_settings() -> Settings:
    return Settings.load()
