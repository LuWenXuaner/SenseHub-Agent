from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from sensehub.api.deps import get_current_user
from sensehub.db import users as user_store
from sensehub.db import wallet as wallet_store
from sensehub.models.schemas import (
    AuthStatus,
    ChangePasswordRequest,
    LoginRequest,
    OAuthProvidersStatus,
    RegisterRequest,
    ResetPasswordRequest,
    SendEmailCodeRequest,
    TokenResponse,
    UserProfile,
)
from sensehub.security.auth import create_access_token
from sensehub.security.email_code import send_verification_code, verify_code
from sensehub.security.oauth_providers import complete_oauth, oauth_configured, start_oauth

router = APIRouter(tags=["auth"])


def _token_response(user: dict, *, remember_me: bool = False) -> TokenResponse:
    hours = 24 * 30 if remember_me else 24
    token = create_access_token(subject=user["username"], hours=hours)
    wallet = wallet_store.ensure_wallet(user["user_id"])
    return TokenResponse(
        access_token=token,
        user=UserProfile(
            username=user["username"],
            display_name=user.get("display_name") or user["username"],
            email=user.get("email") or "",
            public_id=str(wallet.get("public_id") or ""),
            invite_code=str(wallet.get("invite_code") or ""),
            points_balance=int(wallet.get("points_balance") or 0),
        ),
    )


def _profile_from_user(user: dict) -> UserProfile:
    wallet = wallet_store.ensure_wallet(user["user_id"])
    return UserProfile(
        username=user["username"],
        display_name=user.get("display_name") or user["username"],
        email=user.get("email") or "",
        public_id=str(wallet.get("public_id") or ""),
        invite_code=str(wallet.get("invite_code") or ""),
        points_balance=int(wallet.get("points_balance") or 0),
    )


@router.get("/auth/status", response_model=AuthStatus)
async def auth_status():
    count = user_store.count_users()
    return AuthStatus(needs_setup=count == 0, user_count=count)


@router.get("/auth/oauth/status", response_model=OAuthProvidersStatus)
async def oauth_status():
    return OAuthProvidersStatus(
        github=oauth_configured("github"),
        qq=oauth_configured("qq"),
        wechat=oauth_configured("wechat"),
    )


@router.post("/auth/email/send-code")
async def send_email_code(body: SendEmailCodeRequest):
    try:
        return send_verification_code(body.email, purpose=body.purpose or "register")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/auth/register", response_model=TokenResponse)
async def register(body: RegisterRequest):
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="请填写有效邮箱")
    if not verify_code(email, body.code, purpose="register"):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 个字符")
    try:
        user = user_store.create_user_with_email(
            email,
            body.password,
            username=body.username.strip(),
            display_name=body.display_name,
        )
        wallet_store.ensure_wallet(user["user_id"])
        if body.invite_code.strip():
            wallet_store.process_signup_invite(user["user_id"], body.invite_code.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _token_response(user)


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    identifier = (body.email or body.account or body.username or "admin").strip()
    password = body.password

    user = None
    if "@" in identifier:
        user = user_store.authenticate_by_email(identifier.lower(), password)
    else:
        user = user_store.authenticate(identifier.lower(), password)

    if user:
        return _token_response(user, remember_me=body.remember_me)

    from sensehub.security.auth import verify_password

    if identifier.lower() == "admin" and verify_password(password):
        existing = user_store.get_user("admin")
        if not existing:
            user = user_store.create_user("admin", password, display_name="管理员")
            return _token_response(user, remember_me=body.remember_me)
        return _token_response(existing, remember_me=body.remember_me)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")


@router.post("/auth/reset-password")
async def reset_password(body: ResetPasswordRequest):
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="请填写有效邮箱")
    if not verify_code(email, body.code, purpose="reset"):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 个字符")
    try:
        user_store.reset_password_by_email(email, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@router.get("/auth/oauth/{provider}/start")
async def oauth_start(provider: str):
    try:
        return start_oauth(provider.lower())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/auth/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str = "", state: str = ""):
    url = await complete_oauth(provider.lower(), code, state)
    return RedirectResponse(url)


@router.get("/auth/me", response_model=UserProfile)
async def me(username: str = Depends(get_current_user)):
    user = user_store.get_user(username)
    if not user:
        return UserProfile(username=username)
    return _profile_from_user(user)


@router.post("/auth/change-password")
async def change_password(body: ChangePasswordRequest, username: str = Depends(get_current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 个字符")
    try:
        user_store.change_password(username, body.old_password, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}
