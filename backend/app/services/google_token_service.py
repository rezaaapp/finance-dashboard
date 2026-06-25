from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.repositories.google_oauth_repository import update_google_oauth_access_token
from app.security.encryption import decrypt_text, encrypt_text


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
TOKEN_EXPIRY_LEEWAY_SECONDS = 60


class GoogleOAuthTokenError(ValueError):
    pass


class GoogleOAuthNeedsReconnectError(GoogleOAuthTokenError):
    pass


class GoogleOAuthAuthorizationError(GoogleOAuthTokenError):
    pass


def is_google_access_token_expired(oauth_connection: dict) -> bool:
    token_expiry = oauth_connection.get("token_expiry")

    if not token_expiry:
        return False

    if token_expiry.tzinfo is None:
        token_expiry = token_expiry.replace(tzinfo=timezone.utc)

    return token_expiry <= (
        datetime.now(timezone.utc) + timedelta(seconds=TOKEN_EXPIRY_LEEWAY_SECONDS)
    )


def can_refresh_google_access_token(oauth_connection: dict) -> bool:
    return bool(oauth_connection.get("refresh_token_encrypted"))


def get_valid_google_access_token(connection, oauth_connection: dict) -> str:
    encrypted_access_token = oauth_connection.get("access_token_encrypted")

    if not encrypted_access_token:
        raise GoogleOAuthNeedsReconnectError("Google connection is missing access")

    if not is_google_access_token_expired(oauth_connection):
        try:
            return decrypt_text(encrypted_access_token)
        except ValueError as exc:
            raise GoogleOAuthNeedsReconnectError(
                "Google connection could not be used"
            ) from exc

    encrypted_refresh_token = oauth_connection.get("refresh_token_encrypted")
    if not encrypted_refresh_token:
        raise GoogleOAuthNeedsReconnectError("Google connection expired")

    try:
        refresh_token = decrypt_text(encrypted_refresh_token)
    except ValueError as exc:
        raise GoogleOAuthNeedsReconnectError(
            "Google refresh token could not be used"
        ) from exc

    try:
        response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise GoogleOAuthAuthorizationError("Google token refresh failed") from exc

    token_payload = response.json()
    access_token = token_payload.get("access_token")
    if not access_token:
        raise GoogleOAuthAuthorizationError("Google token refresh failed")

    expires_in = int(token_payload.get("expires_in", 3600))
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    try:
        access_token_encrypted = encrypt_text(access_token)
    except ValueError as exc:
        raise GoogleOAuthAuthorizationError("Google token refresh failed") from exc

    update_google_oauth_access_token(
        connection,
        connection_id=str(oauth_connection["id"]),
        access_token_encrypted=access_token_encrypted,
        token_expiry=token_expires_at,
        status="active",
    )

    return access_token
