"""第三方 OAuth（GitHub / QQ / 微信）."""

from __future__ import annotations

import secrets
import uuid
from typing import Any
from urllib.parse import urlencode

import httpx

from sensehub.db import users as user_store
from sensehub.db.database import get_connection
from sensehub.security.auth import create_access_token, hash_password
from sensehub.settings import get_settings

_oauth_states: dict[str, str] = {}


def _frontend_callback(provider: str, *, token: str = "", error: str = "") -> str:
    settings = get_settings()
    base = settings.oauth_frontend_url.rstrip("/")
    q: dict[str, str] = {"provider": provider}
    if token:
        q["token"] = token
    if error:
        q["error"] = error
    return f"{base}/login/oauth/callback?{urlencode(q)}"


def oauth_configured(provider: str) -> bool:
    s = get_settings()
    if provider == "github":
        return bool(s.github_oauth_client_id and s.github_oauth_client_secret)
    if provider == "qq":
        return bool(s.qq_oauth_app_id and s.qq_oauth_app_key)
    if provider == "wechat":
        return bool(s.wechat_oauth_app_id and s.wechat_oauth_app_secret)
    return False


def start_oauth(provider: str) -> dict[str, Any]:
    if not oauth_configured(provider):
        raise RuntimeError(f"{provider} OAuth 未配置，请在 config/local.env 填写密钥")

    settings = get_settings()
    state = secrets.token_urlsafe(16)
    _oauth_states[state] = provider
    redirect_uri = f"http://{settings.api_host}:{settings.api_port}/api/auth/oauth/{provider}/callback"

    if provider == "github":
        params = urlencode(
            {
                "client_id": settings.github_oauth_client_id,
                "redirect_uri": redirect_uri,
                "scope": "read:user user:email",
                "state": state,
            }
        )
        return {"url": f"https://github.com/login/oauth/authorize?{params}", "provider": provider}

    if provider == "qq":
        params = urlencode(
            {
                "response_type": "code",
                "client_id": settings.qq_oauth_app_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "scope": "get_user_info",
            }
        )
        return {"url": f"https://graph.qq.com/oauth2.0/authorize?{params}", "provider": provider}

    if provider == "wechat":
        params = urlencode(
            {
                "appid": settings.wechat_oauth_app_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "snsapi_login",
                "state": state,
            }
        )
        return {"url": f"https://open.weixin.qq.com/connect/qrconnect?{params}#wechat_redirect", "provider": provider}

    raise ValueError(f"不支持的 OAuth: {provider}")


def _upsert_oauth_user(provider: str, provider_uid: str, *, email: str = "", nickname: str = "") -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id FROM oauth_identities WHERE provider = ? AND provider_user_id = ?",
            (provider, provider_uid),
        ).fetchone()
        if row:
            user = user_store.get_user_by_id(row["user_id"])
            if user:
                return user

    base_name = (nickname or f"{provider}_{provider_uid[:8]}").lower()
    base_name = "".join(c if c.isalnum() or c == "_" else "_" for c in base_name)[:20] or f"{provider}_user"
    username = base_name
    i = 1
    while user_store.get_user(username):
        username = f"{base_name}{i}"
        i += 1

    pwd = hash_password(secrets.token_urlsafe(24))
    user = user_store.create_user(
        username,
        password_plain=None,
        password_hash=pwd,
        display_name=nickname or username,
        email=email or None,
    )
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO oauth_identities (id, provider, provider_user_id, user_id)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), provider, provider_uid, user["user_id"]),
        )
    return user


async def complete_oauth(provider: str, code: str, state: str) -> str:
    expected = _oauth_states.pop(state, None)
    if expected != provider:
        return _frontend_callback(provider, error="invalid_state")

    settings = get_settings()
    redirect_uri = f"http://{settings.api_host}:{settings.api_port}/api/auth/oauth/{provider}/callback"

    try:
        if provider == "github":
            user = await _github_user(code, redirect_uri, settings)
        elif provider == "qq":
            user = await _qq_user(code, redirect_uri, settings)
        elif provider == "wechat":
            user = await _wechat_user(code, settings)
        else:
            return _frontend_callback(provider, error="unsupported")
        token = create_access_token(subject=user["username"])
        return _frontend_callback(provider, token=token)
    except Exception as exc:
        return _frontend_callback(provider, error=str(exc)[:120])


async def _github_user(code: str, redirect_uri: str, settings) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_oauth_client_id,
                "client_secret": settings.github_oauth_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        token_resp.raise_for_status()
        access = token_resp.json().get("access_token")
        if not access:
            raise RuntimeError("GitHub 授权失败")
        profile = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access}"},
        )
        profile.raise_for_status()
        data = profile.json()
    return _upsert_oauth_user(
        "github",
        str(data.get("id")),
        email=str(data.get("email") or ""),
        nickname=str(data.get("login") or data.get("name") or ""),
    )


async def _qq_user(code: str, redirect_uri: str, settings) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        token_url = (
            "https://graph.qq.com/oauth2.0/token"
            f"?grant_type=authorization_code&code={code}"
            f"&client_id={settings.qq_oauth_app_id}"
            f"&client_secret={settings.qq_oauth_app_key}"
            f"&redirect_uri={redirect_uri}"
        )
        token_resp = await client.get(token_url)
        token_resp.raise_for_status()
        text = token_resp.text
        if "access_token=" not in text:
            raise RuntimeError("QQ 授权失败")
        access = text.split("access_token=")[1].split("&")[0]
        openid_resp = await client.get(
            f"https://graph.qq.com/oauth2.0/me?access_token={access}&unionid=1"
        )
        openid_resp.raise_for_status()
        raw = openid_resp.text
        import json

        openid_data = json.loads(raw.replace("callback(", "").rstrip(");"))
        openid = openid_data.get("openid", "")
        info = await client.get(
            "https://graph.qq.com/user/get_user_info",
            params={"access_token": access, "oauth_consumer_key": settings.qq_oauth_app_id, "openid": openid},
        )
        info.raise_for_status()
        nick = info.json().get("nickname", "qq_user")
    return _upsert_oauth_user("qq", openid, nickname=nick)


async def _wechat_user(code: str, settings) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        token_resp = await client.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                "appid": settings.wechat_oauth_app_id,
                "secret": settings.wechat_oauth_app_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        data = token_resp.json()
        if data.get("errcode"):
            raise RuntimeError(data.get("errmsg", "微信授权失败"))
        access = data["access_token"]
        openid = data["openid"]
        profile = await client.get(
            "https://api.weixin.qq.com/sns/userinfo",
            params={"access_token": access, "openid": openid},
        )
        profile.raise_for_status()
        info = profile.json()
    return _upsert_oauth_user(
        "wechat",
        openid,
        nickname=str(info.get("nickname") or "wechat_user"),
    )
