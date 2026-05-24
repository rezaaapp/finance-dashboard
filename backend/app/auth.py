from secrets import compare_digest

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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
    is_valid_token = compare_digest(
        credentials.credentials,
        settings.DASHBOARD_AUTH_TOKEN
    )

    if not is_valid_scheme or not is_valid_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    return True
