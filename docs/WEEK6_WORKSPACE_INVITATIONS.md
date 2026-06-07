# Week 6 Workspace Invitations

## Lifecycle

Workspace invitations are stored in `workspace_invitations`. Active access is
still controlled by `workspace_members`.

Statuses:

- `pending`: invitation has been created and is waiting for the invited user.
- `accepted`: invited user accepted and was added to `workspace_members`.
- `declined`: invited user declined and was not added to the workspace.
- `cancelled`: owner/admin cancelled a pending invitation.
- `expired`: reserved for future expiry handling.

MVP role:

- `member`

Owner invitations are not supported by the MVP invitation flow.

## Create Invitation

Endpoint:

```text
POST /api/workspaces/{workspace_id}/invitations
```

Rules:

- Auth is required.
- Current user must be owner/admin of the target workspace.
- Email is normalized to lowercase.
- Existing active members return `409 Already a member`.
- Duplicate pending invitations return `409 Invitation already pending`.
- A pending invitation does not create a `workspace_members` row.
- No email is sent in the MVP flow.
- No token or secret is returned.

## Pending Invitations

Endpoint:

```text
GET /api/workspace-invitations/pending
```

The backend returns only pending invitations matching the authenticated user's
email. If `invited_user_id` is empty and the invited user has logged in, the
pending row can be linked to that user ID.

## Accept Flow

Endpoint:

```text
POST /api/workspace-invitations/{invitation_id}/accept
```

Rules:

- Auth is required.
- Current user's email must match the invitation email.
- Invitation must be `pending`.
- The user is added to `workspace_members` if missing.
- The invitation status becomes `accepted`.
- `responded_at` is set.
- `GET /api/workspaces` includes the workspace after accept.

Frontend behavior:

- Pending invitation notification removes the accepted invitation.
- Workspace list is refreshed.
- Accepted workspace is auto-selected.
- Dashboard/Configuration reload through the existing active workspace flow.

## Decline Flow

Endpoint:

```text
POST /api/workspace-invitations/{invitation_id}/decline
```

Rules:

- Auth is required.
- Current user's email must match the invitation email.
- Invitation must be `pending`.
- The invitation status becomes `declined`.
- No `workspace_members` row is created.

## Cancel Flow

Endpoint:

```text
DELETE /api/workspaces/{workspace_id}/invitations/{invitation_id}
```

Rules:

- Auth is required.
- Current user must be owner/admin of the workspace.
- Invitation must belong to the workspace and be `pending`.
- The invitation status becomes `cancelled`.
- Invitations are not hard deleted.

## Existing Member Compatibility

Existing `workspace_members` rows remain the source of active access. Existing
members do not need to accept a new invitation.

Expected Divya scenario:

1. Divya is already a member of Reza workspace through `workspace_members`.
2. Divya logs in.
3. Reza workspace still appears in the workspace switcher.
4. Divya does not see an acceptance requirement for that existing membership.

## Security Rules

- Users cannot view pending invitations for another email.
- Users cannot accept or decline invitations for another email.
- Members cannot create or cancel invitations.
- Invitations cannot create owner role access.
- Duplicate pending invitations are blocked by a partial unique index.
- Invitation tokens are not used or returned by the MVP API.
- User-facing errors are safe `400`, `403`, `404`, or `409` messages.

## Manual QA Checklist

Owner invite:

1. Login as `rezaaapp@gmail.com`.
2. Select Reza workspace.
3. Open Configuration > Workspace Members.
4. Invite a new email.
5. Confirm the invite appears under Pending Invitations.
6. Confirm the user does not appear under Current Members.

Accept:

1. Login as the invited email.
2. Confirm the header shows a pending invitation notification.
3. Click Accept.
4. Confirm the workspace appears in the switcher.
5. Confirm the accepted workspace is selected and Dashboard loads it.

Decline:

1. Create another invite.
2. Login as the invited email.
3. Click Decline.
4. Confirm the workspace does not appear in the switcher.

Cancel:

1. Login as owner/admin.
2. Create a pending invite.
3. Click Cancel Invite.
4. Confirm the pending invitation disappears.
5. Confirm the invited user no longer sees it.

Security negative:

1. Attempt to accept an invitation for another email.
2. Confirm a safe `403` or `404` response.
3. Attempt to cancel as a non-owner/non-admin.
4. Confirm a safe `403` response.

## Known Limitations

- Email delivery is not implemented yet.
- Invitation expiry is schema-ready but not automatically enforced.
- MVP invitations only support the `member` role.
