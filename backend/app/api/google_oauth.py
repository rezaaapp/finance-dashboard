import logging
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.auth import require_current_user
from app.config import settings
from app.database import get_db_connection
from app.repositories.google_oauth_repository import upsert_google_oauth_connection
from app.security.encryption import encrypt_text
from app.security.oauth_state import create_oauth_state, verify_oauth_state
from app.services.google_oauth import (
    build_google_authorization_url,
    exchange_authorization_code,
    extract_email_from_id_token,
    fetch_google_user_profile,
)
from app.api.google_connection import get_current_workspace


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/google/oauth",
    tags=["Google OAuth"],
)


def _log_callback_step(step: str, *, reason: str | None = None):
    log_method = logger.warning if step.endswith("_failed") else logger.info
    log_method("google_oauth_callback step=%s reason=%s", step, reason or "none")


def _frontend_redirect(status: str, reason: str | None = None):
    params_payload = {"google_connected": status}

    if status == "failed" and reason:
        params_payload["reason"] = reason

    params = urlencode(params_payload)
    frontend_url = settings.FRONTEND_URL.rstrip("/")

    return RedirectResponse(
        f"{frontend_url}/settings/data-sources?{params}",
        status_code=302,
    )


@router.get("/start")
def start_google_oauth(
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    try:
        state = create_oauth_state(
            user_id=current_user["sub"],
            workspace_id=str(workspace["id"]),
        )
        auth_url = build_google_authorization_url(state=state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured",
        ) from exc

    return {"auth_url": auth_url}


@router.get("/callback")
async def google_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    _log_callback_step("oauth_callback_received")

    if error:
        _log_callback_step("google_error_received", reason="google_error")
        _log_callback_step("redirect_failed", reason="google_error")
        return _frontend_redirect("failed", reason="google_error")

    if not code or not state:
        _log_callback_step("redirect_failed", reason="unknown")
        return _frontend_redirect("failed", reason="unknown")

    try:
        _log_callback_step("state_verify_started")
        state_payload = verify_oauth_state(state)
        _log_callback_step("state_verify_success")
    except ValueError:
        _log_callback_step("state_verify_failed", reason="invalid_state")
        _log_callback_step("redirect_failed", reason="invalid_state")
        return _frontend_redirect("failed", reason="invalid_state")

    try:
        _log_callback_step("token_exchange_started")
        tokens = await exchange_authorization_code(code=code)
        _log_callback_step("token_exchange_success")
    except (httpx.HTTPError, KeyError, ValueError):
        _log_callback_step(
            "token_exchange_failed",
            reason="token_exchange_failed",
        )
        _log_callback_step("redirect_failed", reason="token_exchange_failed")
        return _frontend_redirect("failed", reason="token_exchange_failed")

    profile = {
        "email": None,
        "name": None,
        "avatar_url": None,
    }

    try:
        _log_callback_step("userinfo_fetch_started")
        profile = await fetch_google_user_profile(
            access_token=tokens["access_token"],
        )
        if not profile.get("email"):
            profile["email"] = extract_email_from_id_token(
                tokens.get("id_token")
            )
        _log_callback_step("userinfo_fetch_success")
    except (httpx.HTTPError, KeyError, ValueError):
        _log_callback_step("userinfo_fetch_failed", reason="userinfo_failed")

        profile["email"] = extract_email_from_id_token(tokens.get("id_token"))

    try:
        _log_callback_step("encryption_started")
        access_token_encrypted = encrypt_text(tokens["access_token"])
        refresh_token = tokens.get("refresh_token")
        refresh_token_encrypted = (
            encrypt_text(refresh_token) if refresh_token else None
        )
        _log_callback_step("encryption_success")
    except (KeyError, ValueError):
        _log_callback_step("encryption_failed", reason="encryption_failed")
        _log_callback_step("redirect_failed", reason="encryption_failed")
        return _frontend_redirect("failed", reason="encryption_failed")

    try:
        _log_callback_step("db_upsert_started")
        with get_db_connection() as connection:
            with connection.transaction():
                upsert_google_oauth_connection(
                    connection,
                    workspace_id=state_payload["workspace_id"],
                    user_id=state_payload["user_id"],
                    google_email=profile["email"],
                    access_token_encrypted=access_token_encrypted,
                    refresh_token_encrypted=refresh_token_encrypted,
                    token_expiry=tokens["token_expires_at"],
                    scopes=tokens["scope"],
                    status="active",
                )
        _log_callback_step("db_upsert_success")
    except Exception:
        _log_callback_step(
            "db_upsert_failed",
            reason="database_upsert_failed",
        )
        _log_callback_step("redirect_failed", reason="database_upsert_failed")
        return _frontend_redirect("failed", reason="database_upsert_failed")

    _log_callback_step("redirect_success")
    return _frontend_redirect("success")
