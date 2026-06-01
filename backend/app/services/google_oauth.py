from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt

from app.config import settings


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_AUTH_REQUIRED_PARAMS = {
    "client_id",
    "redirect_uri",
    "response_type",
    "scope",
    "state",
    "access_type",
    "prompt",
}


def build_google_authorization_url(
    *,
    state: str,
    redirect_uri: str | None = None,
):
    settings.require_google_oauth_settings()
    callback_uri = redirect_uri or settings.GOOGLE_OAUTH_REDIRECT_URI

    params = [
        ("client_id", settings.GOOGLE_OAUTH_CLIENT_ID),
        ("redirect_uri", callback_uri),
        ("response_type", "code"),
        ("scope", settings.GOOGLE_OAUTH_SCOPES),
        ("state", state),
        ("access_type", "offline"),
        ("prompt", "consent"),
    ]
    param_names = {name for name, value in params if value}
    missing_params = GOOGLE_AUTH_REQUIRED_PARAMS - param_names

    if missing_params:
        raise ValueError(
            "Google OAuth authorization URL is missing required parameters"
        )

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_authorization_code(
    *,
    code: str,
    redirect_uri: str | None = None,
):
    settings.require_google_oauth_settings()
    callback_uri = redirect_uri or settings.GOOGLE_OAUTH_REDIRECT_URI

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": callback_uri,
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
        "id_token": token_payload.get("id_token"),
        "token_expires_at": token_expires_at,
        "scope": token_payload.get("scope") or settings.GOOGLE_OAUTH_SCOPES,
    }


def extract_email_from_id_token(id_token: str | None) -> str | None:
    if not id_token:
        return None

    try:
        payload = jwt.decode(
            id_token,
            options={
                "verify_signature": False,
                "verify_aud": False,
            },
            algorithms=["RS256"],
        )
    except jwt.PyJWTError:
        return None

    email = payload.get("email")
    return email.lower() if email else None


async def fetch_google_user_profile(*, access_token: str):
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    response.raise_for_status()
    profile = response.json()
    email = profile.get("email")

    return {
        "email": email.lower() if email else None,
        "name": profile.get("name") or (email.split("@")[0] if email else None),
        "avatar_url": profile.get("picture"),
    }
