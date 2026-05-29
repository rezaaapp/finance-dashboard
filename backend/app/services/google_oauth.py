from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.config import settings


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_SCOPES = (
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/spreadsheets",
)


def build_google_authorization_url(*, state: str):
    settings.require_google_oauth_settings()

    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_authorization_code(*, code: str):
    settings.require_google_oauth_settings()

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            },
        )

    response.raise_for_status()
    token_payload = response.json()
    expires_in = int(token_payload.get("expires_in", 3600))
    token_expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    )

    return {
        "access_token": token_payload["access_token"],
        "refresh_token": token_payload.get("refresh_token"),
        "token_expires_at": token_expires_at,
    }


async def fetch_google_user_profile(*, access_token: str):
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    response.raise_for_status()
    profile = response.json()

    return {
        "email": profile["email"],
        "name": profile.get("name") or profile["email"].split("@")[0],
        "avatar_url": profile.get("picture"),
    }
