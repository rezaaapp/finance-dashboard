from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

import jwt

from app.config import settings


STATE_TTL_MINUTES = 10


def create_oauth_state(user_id: str, workspace_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "purpose": "google_oauth",
        "user_id": user_id,
        "workspace_id": workspace_id,
        "nonce": token_urlsafe(24),
        "created_at": int(now.timestamp()),
        "iat": now,
        "exp": now + timedelta(minutes=STATE_TTL_MINUTES),
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_oauth_state(state: str) -> dict:
    try:
        payload = jwt.decode(state, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("OAuth state has expired") from exc
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid OAuth state") from exc

    required_fields = ("user_id", "workspace_id", "nonce", "created_at")

    if payload.get("purpose") != "google_oauth":
        raise ValueError("Invalid OAuth state")

    if any(not payload.get(field) for field in required_fields):
        raise ValueError("Invalid OAuth state")

    return {
        "user_id": payload["user_id"],
        "workspace_id": payload["workspace_id"],
        "nonce": payload["nonce"],
        "created_at": payload["created_at"],
    }
