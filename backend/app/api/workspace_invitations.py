from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_current_user
from app.database import get_db_connection
from app.repositories.workspace_invitation_repository import (
    accept_invitation,
    add_workspace_member_if_missing,
    cancel_invitation,
    create_workspace_invitation,
    decline_invitation,
    get_invitation_by_id,
    get_pending_invitations_for_email,
    get_pending_invitations_for_workspace,
    has_pending_invitation,
    is_active_workspace_member_by_email,
    normalize_invitation_email,
)
from app.repositories.workspaces import get_workspace_for_user
from app.security.workspace_permissions import require_workspace_manager


router = APIRouter(tags=["Workspace Invitations"])

ALLOWED_INVITATION_ROLES = {"member"}


class WorkspaceInvitationCreate(BaseModel):
    email: str
    role: str = "member"


def _validate_email(email: str) -> str:
    normalized_email = normalize_invitation_email(email)

    if not normalized_email or "@" not in normalized_email:
        raise HTTPException(status_code=400, detail="Valid email is required")

    return normalized_email


def _validate_role(role: str) -> str:
    normalized_role = str(role or "member").strip().lower()

    if normalized_role not in ALLOWED_INVITATION_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Only member invitations are supported.",
        )

    return normalized_role


def _serialize_invitation(invitation):
    return {
        "id": str(invitation["id"]),
        "workspace_id": str(invitation["workspace_id"]),
        "email": invitation.get("email"),
        "role": invitation["role"],
        "status": invitation["status"],
        "created_at": invitation["created_at"],
        "expires_at": invitation.get("expires_at"),
        "responded_at": invitation.get("responded_at"),
    }


def _serialize_pending_invitation(invitation):
    return {
        "id": str(invitation["id"]),
        "workspace_id": str(invitation["workspace_id"]),
        "workspace_name": invitation["workspace_name"],
        "role": invitation["role"],
        "invited_by_name": invitation.get("invited_by_name"),
        "invited_by_email": invitation.get("invited_by_email"),
        "created_at": invitation["created_at"],
        "expires_at": invitation.get("expires_at"),
    }


def _serialize_workspace_pending_invitation(invitation):
    return {
        **_serialize_invitation(invitation),
        "invited_by_name": invitation.get("invited_by_name"),
        "invited_by_email": invitation.get("invited_by_email"),
    }


def _get_workspace_with_invite_permission(connection, *, current_user, workspace_id: str):
    workspace = get_workspace_for_user(
        connection,
        user_id=current_user["sub"],
        workspace_id=workspace_id,
    )

    if not workspace:
        raise HTTPException(status_code=403, detail="Workspace access denied")

    return require_workspace_manager(
        current_user=current_user,
        workspace=workspace,
        detail="Only workspace owners can manage invitations.",
    )


@router.post("/api/workspaces/{workspace_id}/invitations")
def create_invitation(
    workspace_id: str,
    payload: WorkspaceInvitationCreate,
    current_user=Depends(require_current_user),
):
    email = _validate_email(payload.email)
    role = _validate_role(payload.role)

    with get_db_connection() as connection:
        with connection.transaction():
            _get_workspace_with_invite_permission(
                connection,
                current_user=current_user,
                workspace_id=workspace_id,
            )

            if is_active_workspace_member_by_email(
                connection,
                workspace_id=workspace_id,
                email=email,
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Already a member",
                )

            if has_pending_invitation(
                connection,
                workspace_id=workspace_id,
                email=email,
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Invitation already pending",
                )

            invitation = create_workspace_invitation(
                connection,
                workspace_id=workspace_id,
                email=email,
                role=role,
                invited_by_user_id=current_user["sub"],
            )

    return _serialize_invitation(invitation)


@router.get("/api/workspaces/{workspace_id}/invitations")
def list_workspace_pending_invitations(
    workspace_id: str,
    current_user=Depends(require_current_user),
):
    with get_db_connection() as connection:
        _get_workspace_with_invite_permission(
            connection,
            current_user=current_user,
            workspace_id=workspace_id,
        )
        invitations = get_pending_invitations_for_workspace(
            connection,
            workspace_id=workspace_id,
        )

    return {
        "invitations": [
            _serialize_workspace_pending_invitation(invitation)
            for invitation in invitations
        ],
    }


@router.get("/api/workspace-invitations/pending")
def list_pending_invitations(current_user=Depends(require_current_user)):
    email = _validate_email(current_user.get("email", ""))

    with get_db_connection() as connection:
        with connection.transaction():
            invitations = get_pending_invitations_for_email(
                connection,
                email=email,
                user_id=current_user["sub"],
            )

    return {
        "invitations": [
            _serialize_pending_invitation(invitation)
            for invitation in invitations
        ],
    }


@router.post("/api/workspace-invitations/{invitation_id}/accept")
def accept_workspace_invitation(
    invitation_id: str,
    current_user=Depends(require_current_user),
):
    email = _validate_email(current_user.get("email", ""))

    with get_db_connection() as connection:
        with connection.transaction():
            invitation = get_invitation_by_id(
                connection,
                invitation_id=invitation_id,
            )

            if not invitation:
                raise HTTPException(status_code=404, detail="Invitation not found")

            if normalize_invitation_email(invitation["email"]) != email:
                raise HTTPException(status_code=403, detail="Invitation access denied")

            if invitation["status"] != "pending":
                raise HTTPException(
                    status_code=409,
                    detail="Invitation is not pending",
                )

            accepted_invitation = accept_invitation(
                connection,
                invitation_id=invitation_id,
                user_id=current_user["sub"],
                email=email,
            )

            if not accepted_invitation:
                raise HTTPException(
                    status_code=409,
                    detail="Invitation is not pending",
                )

            member = add_workspace_member_if_missing(
                connection,
                workspace_id=str(accepted_invitation["workspace_id"]),
                user_id=current_user["sub"],
                role=accepted_invitation["role"],
            )

    return {
        "status": "accepted",
        "workspace": {
            "id": str(accepted_invitation["workspace_id"]),
            "name": invitation["workspace_name"],
            "role": member["role"],
        },
    }


@router.post("/api/workspace-invitations/{invitation_id}/decline")
def decline_workspace_invitation(
    invitation_id: str,
    current_user=Depends(require_current_user),
):
    email = _validate_email(current_user.get("email", ""))

    with get_db_connection() as connection:
        with connection.transaction():
            invitation = get_invitation_by_id(
                connection,
                invitation_id=invitation_id,
            )

            if not invitation:
                raise HTTPException(status_code=404, detail="Invitation not found")

            if normalize_invitation_email(invitation["email"]) != email:
                raise HTTPException(status_code=403, detail="Invitation access denied")

            if invitation["status"] != "pending":
                raise HTTPException(
                    status_code=409,
                    detail="Invitation is not pending",
                )

            declined_invitation = decline_invitation(
                connection,
                invitation_id=invitation_id,
                user_id=current_user["sub"],
                email=email,
            )

            if not declined_invitation:
                raise HTTPException(
                    status_code=409,
                    detail="Invitation is not pending",
                )

    return {
        "status": "declined",
        "invitation": _serialize_invitation(declined_invitation),
    }


@router.delete("/api/workspaces/{workspace_id}/invitations/{invitation_id}")
def cancel_workspace_invitation(
    workspace_id: str,
    invitation_id: str,
    current_user=Depends(require_current_user),
):
    with get_db_connection() as connection:
        with connection.transaction():
            _get_workspace_with_invite_permission(
                connection,
                current_user=current_user,
                workspace_id=workspace_id,
            )

            cancelled_invitation = cancel_invitation(
                connection,
                workspace_id=workspace_id,
                invitation_id=invitation_id,
            )

            if not cancelled_invitation:
                raise HTTPException(
                    status_code=404,
                    detail="Pending invitation not found",
                )

    return {
        "status": "cancelled",
        "invitation": _serialize_invitation(cancelled_invitation),
    }
