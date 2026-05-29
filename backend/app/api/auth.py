from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.auth import (
    authenticate_user,
    create_internal_token,
    create_oauth_state,
    verify_oauth_state,
)
from app.config import settings
from app.database import get_db_connection
from app.repositories.users import upsert_user, upsert_user_tokens
from app.repositories.workspaces import ensure_default_workspace_for_user
from app.services.google_oauth import (
    build_google_authorization_url,
    exchange_authorization_code,
    fetch_google_user_profile,
)
from app.services.token_crypto import encrypt_token


router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest):
    if not authenticate_user(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return {
        "token": settings.DASHBOARD_AUTH_TOKEN,
        "username": payload.username,
    }


@router.get("/google")
def google_login():
    try:
        authorization_url = build_google_authorization_url(
            state=create_oauth_state()
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return RedirectResponse(authorization_url, status_code=status.HTTP_302_FOUND)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = None,
):
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth failed: {error}",
        )

    verify_oauth_state(state)

    try:
        tokens = await exchange_authorization_code(code=code)
        profile = await fetch_google_user_profile(
            access_token=tokens["access_token"]
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google OAuth token exchange failed",
        ) from exc

    try:
        with get_db_connection() as connection:
            with connection.transaction():
                user = upsert_user(
                    connection,
                    email=profile["email"],
                    name=profile["name"],
                    avatar_url=profile["avatar_url"],
                )
                upsert_user_tokens(
                    connection,
                    user_id=str(user["id"]),
                    access_token=encrypt_token(tokens["access_token"]),
                    refresh_token=encrypt_token(tokens["refresh_token"])
                    if tokens["refresh_token"]
                    else None,
                    token_expires_at=tokens["token_expires_at"],
                )
                workspace = ensure_default_workspace_for_user(
                    connection,
                    user_id=str(user["id"]),
                    user_name=user["name"],
                )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    internal_token = create_internal_token(user)

    if settings.FRONTEND_AUTH_REDIRECT_URL:
        redirect_params = urlencode({
            "token": internal_token,
            "user_id": str(user["id"]),
            "email": user["email"],
            "name": user["name"],
            "workspace_id": str(workspace["id"]),
        })

        return RedirectResponse(
            f"{settings.FRONTEND_AUTH_REDIRECT_URL}#{redirect_params}",
            status_code=status.HTTP_302_FOUND,
        )

    return {
        "token": internal_token,
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "name": user["name"],
            "avatar_url": user["avatar_url"],
        },
        "workspace": {
            "id": str(workspace["id"]),
            "name": workspace["name"],
            "role": workspace["role"],
            "google_sheet_id": workspace["google_sheet_id"],
            "google_sheet_sources": workspace["google_sheet_sources"] or [],
        },
    }
