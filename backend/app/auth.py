from secrets import compare_digest
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from app.config import settings


security = HTTPBearer(auto_error=False)


def authenticate_user(username: str, password: str):
    is_valid_username = compare_digest(
        username,
        settings.DASHBOARD_USERNAME
    )
    is_valid_password = compare_digest(
        password,
        settings.DASHBOARD_PASSWORD
    )

    return is_valid_username and is_valid_password


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    is_valid_scheme = credentials.scheme.lower() == "bearer"

    if not is_valid_scheme:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    bearer_token = credentials.credentials
    is_static_token = compare_digest(
        bearer_token,
        settings.DASHBOARD_AUTH_TOKEN
    )

    if is_static_token:
        return True

    try:
        return jwt.decode(
            bearer_token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc


def require_current_user(
    auth_payload=Depends(require_auth),
):
    if auth_payload is True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session required",
        )

    return auth_payload


def require_super_admin(auth_payload=Depends(require_auth)):
    if auth_payload is True:
        return {
            "sub": "legacy-admin",
            "email": settings.DASHBOARD_USERNAME,
            "name": settings.DASHBOARD_USERNAME,
            "role": "super_admin",
        }

    if auth_payload.get("role") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )

    return auth_payload


def require_premium_role(auth_payload=Depends(require_auth)):
    if auth_payload is True:
        return auth_payload

    if auth_payload.get("role") not in {"super_admin", "owner", "member"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium access required",
        )

    return auth_payload


def create_internal_token(user):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRES_IN_MINUTES),
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_oauth_state():
    now = datetime.now(timezone.utc)
    payload = {
        "purpose": "google_oauth",
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_oauth_state(state: str):
    try:
        payload = jwt.decode(state, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        ) from exc

    if payload.get("purpose") != "google_oauth":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )
