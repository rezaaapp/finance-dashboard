from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.auth import authenticate_user
from app.config import settings


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
