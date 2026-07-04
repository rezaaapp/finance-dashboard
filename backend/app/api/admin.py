from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import re

from app.auth import create_internal_token, require_super_admin
from app.database import get_db_connection
from app.repositories.users import (
    create_user,
    delete_user,
    get_user_by_id,
    list_users,
    update_user,
    update_user_role,
)
from app.services.uat_user_provisioning import (
    is_uat_provisioning_allowed,
    provision_test_user,
)


router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    dependencies=[Depends(require_super_admin)],
)


class UserRoleUpdate(BaseModel):
    role: str


class AdminUserCreate(BaseModel):
    email: str
    name: str
    role: str = "user"


class AdminUserUpdate(BaseModel):
    email: str
    name: str
    role: str


class UatTestUserProvision(BaseModel):
    email: str
    name: str
    role: str = "owner"
    password: str
    workspace_name: str


VALID_ROLES = {"super_admin", "owner", "member", "user"}


def validate_role(role: str):
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'super_admin', 'owner', 'member', or 'user'",
        )


def serialize_user(user):
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "name": user["name"],
        "avatar_url": user["avatar_url"],
        "role": user["role"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }


@router.get("/users")
def get_users():
    with get_db_connection() as connection:
        users = list_users(connection)

    return {"users": [serialize_user(user) for user in users]}


@router.post("/users", status_code=status.HTTP_201_CREATED)
def post_user(payload: AdminUserCreate):
    validate_role(payload.role)

    email = payload.email.strip().lower()
    name = payload.name.strip()

    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid email is required",
        )

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is required",
        )

    try:
        with get_db_connection() as connection:
            user = create_user(
                connection,
                email=email,
                name=name,
                role=payload.role,
            )
    except Exception as exc:
        if "users_email_key" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            ) from exc

        raise

    return {"user": serialize_user(user)}


@router.post("/users/provision-test-user", status_code=status.HTTP_201_CREATED)
def provision_uat_test_user(payload: UatTestUserProvision):
    if not is_uat_provisioning_allowed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provisioning user tester hanya tersedia di DEV atau UAT.",
        )

    email = payload.email.strip().lower()
    name = payload.name.strip()
    workspace_name = payload.workspace_name.strip()

    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Masukkan email yang valid.",
        )
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nama wajib diisi.",
        )
    if not workspace_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nama workspace wajib diisi.",
        )

    try:
        with get_db_connection() as connection:
            with connection.transaction():
                result = provision_test_user(
                    connection,
                    email=email,
                    name=name,
                    role=payload.role,
                    password=payload.password,
                    workspace_name=workspace_name,
                )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        if "users_email_key" in str(exc) or "duplicate key" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email tersebut sudah terdaftar.",
            ) from exc
        raise

    return {
        "created": True,
        "user_id": str(result["user"]["id"]),
        "workspace_id": str(result["workspace"]["id"]),
        "email": result["user"]["email"],
        "name": result["user"]["name"],
        "role": result["user"]["role"],
        "workspace_name": result["workspace"]["name"],
        "user": serialize_user(result["user"]),
    }


@router.put("/users/{user_id}")
def put_user(user_id: str, payload: AdminUserUpdate):
    validate_role(payload.role)

    email = payload.email.strip().lower()
    name = payload.name.strip()

    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid email is required",
        )

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is required",
        )

    try:
        with get_db_connection() as connection:
            user = update_user(
                connection,
                user_id=user_id,
                email=email,
                name=name,
                role=payload.role,
            )
    except Exception as exc:
        if "users_email_key" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            ) from exc

        raise

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {"user": serialize_user(user)}


@router.patch("/users/{user_id}/role")
def patch_user_role(user_id: str, payload: UserRoleUpdate):
    validate_role(payload.role)

    with get_db_connection() as connection:
        user = update_user_role(
            connection,
            user_id=user_id,
            role=payload.role,
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {"user": serialize_user(user)}


@router.post("/users/{user_id}/impersonate")
def impersonate_user(user_id: str):
    with get_db_connection() as connection:
        user = get_user_by_id(connection, user_id=user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "token": create_internal_token(user),
        "user": serialize_user(user),
    }


@router.delete("/users/{user_id}")
def remove_user(user_id: str):
    with get_db_connection() as connection:
        user = delete_user(connection, user_id=user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {"user": serialize_user(user)}
