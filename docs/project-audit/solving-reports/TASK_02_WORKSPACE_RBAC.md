# Solving Report - Task 2

## Summary

Workspace management authorization now uses the role from
`workspace_members` instead of comparing workspace permissions against the
global user role.

A centralized workspace permission policy is used by:

- workspace configuration updates
- dashboard member invitations
- workspace invitation create/list/cancel authorization

## Root Cause

`update_workspace_configuration` previously checked:

```text
current_user.role == "member"
```

The JWT/global user role uses values such as `user` and `super_admin`.
Workspace membership uses `owner` and `member`. Because these are separate
role domains, a normal user with workspace role `member` was not rejected by
the global-role comparison.

Invitation endpoints also duplicated their own role checks, increasing the
chance of inconsistent authorization behavior.

## Impact Area

- `PUT /api/dashboard/workspace/configuration`
- `POST /api/dashboard/workspace/members`
- `POST /api/workspaces/{workspace_id}/invitations`
- `GET /api/workspaces/{workspace_id}/invitations`
- `DELETE /api/workspaces/{workspace_id}/invitations/{invitation_id}`

Read-only workspace configuration and member-list endpoints remain available
to active workspace members.

## Files Changed

- `backend/app/security/workspace_permissions.py`
- `backend/app/api/dashboard.py`
- `backend/app/api/workspace_invitations.py`
- `backend/tests/test_workspace_permissions.py`

## Technical Changes

- Added `can_manage_workspace`.
- Added `require_workspace_manager`.
- Permission decisions now evaluate:

  ```text
  workspace.role
  ```

  from the resolved workspace membership.

- Global `super_admin` remains an administrative override, but the request must
  still resolve an accessible workspace first.
- Unknown workspace roles are denied by default.
- Removed the incorrect global-role member check from workspace configuration.
- Reused the same policy for invitation management.

## Role Matrix

| Global Role | Workspace Role | Update Config | Manage Invitations |
|---|---|---:|---:|
| `user` | `owner` | Allowed | Allowed |
| `user` | `member` | Denied | Denied |
| `super_admin` | `owner` | Allowed | Allowed |
| `super_admin` | `member` | Allowed | Allowed |
| `user` | unknown / missing | Denied | Denied |
| any | no accessible workspace | Denied | Denied |

The current database constraint supports workspace roles `owner` and `member`.
There is no workspace-level `admin` role yet. Administrative override currently
means global `super_admin`.

## Validation

Commands:

```text
python -m unittest backend.tests.test_workspace_permissions
python -m unittest discover -s backend/tests -t .
python -m compileall -q backend/app backend/scripts
npm run lint
git diff --check
```

Results:

- Workspace permission tests: `6` passed.
- Full backend tests: `79` passed.
- Backend compile: passed.
- Dashboard and landing lint: passed.
- Diff whitespace validation: passed.
- Regression contract verifies the configuration endpoint invokes the central
  policy and no longer reads `current_user.role` for workspace authorization.

No migration was executed locally, on staging, or in production during Task 2.
Migration 019 remains pending staging/checkpoint validation.

## Result

Successful.

## Remaining Risk

- Global `super_admin` remains powerful and should eventually be protected by
  stronger session controls and audit logging.
- Other workspace mutations such as data-source create/delete/sync and insight
  settings currently allow active members. Their desired product permission
  matrix should be specified before tightening them.
- A workspace-level `admin` role requires an explicit schema and product
  decision; it is not silently accepted by the new policy.
- Browser E2E with real owner/member accounts remains part of the Task 1–3
  checkpoint.

## Commit

Message:

```text
fix(auth): enforce workspace role permissions
```

The commit hash is reported after the commit is created.

## Follow-up Findings

- Frontend configuration UI already hides invitation management from regular
  members, but server authorization is the definitive control.
- Data-source and insight-setting permissions need a separate role-matrix
  decision rather than being expanded implicitly in this task.

