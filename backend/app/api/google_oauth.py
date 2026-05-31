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
    fetch_google_user_profile,
)
from app.api.google_connection import get_current_workspace


router = APIRouter(
    prefix="/api/google/oauth",
    tags=["Google OAuth"],
)


def _frontend_redirect(status: str):
    params = urlencode({"google_connected": status})
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
    if error or not code or not state:
        return _frontend_redirect("failed")

    try:
        state_payload = verify_oauth_state(state)
    except ValueError:
        return _frontend_redirect("failed")

    try:
        tokens = await exchange_authorization_code(code=code)
        profile = await fetch_google_user_profile(
            access_token=tokens["access_token"],
        )
        access_token_encrypted = encrypt_text(tokens["access_token"])
        refresh_token = tokens.get("refresh_token")
        refresh_token_encrypted = (
            encrypt_text(refresh_token) if refresh_token else None
        )
    except (httpx.HTTPError, KeyError, ValueError):
        return _frontend_redirect("failed")

    try:
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
    except Exception:
        return _frontend_redirect("failed")

    return _frontend_redirect("success")
