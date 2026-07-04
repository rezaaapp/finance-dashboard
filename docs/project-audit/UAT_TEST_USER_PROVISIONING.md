# UAT Test User Provisioning

## Background

Omon previously allowed Super Admin to create a user record from User Management, but that record did not have an independent password, workspace, owner membership, or ready-to-use workspace configuration. A tester therefore could not immediately Login and complete the real first-time Google Sheet journey.

This change adds an internal provisioning workflow for LOCAL DEV, DEV, and UAT. It is not production self-signup.

## Why DBeaver or Manual Inserts Are Not Ideal

Manual inserts require knowledge of several related tables and make it easy to create an orphan user, omit owner membership, skip default configuration, or store a credential incorrectly. They also provide no reliable rollback across steps and encourage sharing credentials outside the controlled one-time UI.

The application workflow applies validation, access/environment gates, secure hashing, and one database transaction consistently.

## New Provisioning Workflow

From User Management, a Super Admin selects `Provision UAT User` and provides:

- Email
- Name
- Role (`owner`, `member`, or `user`; `super_admin` is intentionally excluded)
- Password, entered manually or generated in the browser
- Workspace Name, defaulted from the tester name as `<Name>'s Household`

The frontend calls:

`POST /api/admin/users/provision-test-user`

After success, a one-time credential dialog shows the application URL, email, plaintext password, and workspace. `Copy Credential` copies the details plus the tester path:

`Login → Settings → Connect Google → Add Spreadsheet URL → Test Connection → Save Source → Sync Now → Dashboard`

Closing the dialog clears the plaintext password from UI state. The backend response never returns it.

## Access Control

- The existing Admin router requires `super_admin` for every endpoint.
- The provisioning endpoint adds a backend environment gate for `local-dev`, `dev`, or `uat` using `APP_ENV`/`ENV_PROFILE`.
- `local-prod` and other production profiles receive HTTP 403.
- The frontend independently hides the provisioning action unless system information reports a safe environment/profile.
- This defense in depth does not rely on the frontend for authorization.

## Data Created

One transaction creates:

1. `users` row with the selected global role.
2. `user_password_credentials` row containing only a PBKDF2-SHA256 hash.
3. `workspaces` row.
4. `workspace_members` row with the tester as workspace `owner`.
5. `workspace_configurations` row with the existing empty/default Sheet configuration.

Migration `022_add_user_password_credentials.sql` adds the one-to-one credential table with cascade deletion and updated-at behavior.

If any operation fails, the connection transaction rolls back all five operations.

## Data Preserved

- Existing users, workspaces, memberships, and configurations are unchanged.
- Existing static local-admin Login remains supported.
- Google OAuth, Google Sheet Sync, Import Transparency, Safe Reset, Blu PDF Import, and analytics logic are unchanged.
- Existing user deletion semantics remain unchanged; credential deletion follows the user foreign-key cascade.

## Security Notes

- Passwords are hashed with PBKDF2-HMAC-SHA256, a random 16-byte salt, and 600,000 iterations.
- Strength requires at least 10 characters, uppercase, lowercase, number, and symbol.
- Plaintext is never stored or logged and is not returned by the API.
- Password hashes are never included in user list/detail responses.
- Login uses constant-time digest comparison through the password verification helper.
- Email is normalized and validated; duplicate email returns a safe conflict response.
- Provisioned roles exclude `super_admin` to prevent this UAT helper from creating another global administrator.
- Workspace owner membership ensures isolation and lets the tester configure only their own workspace.

## Tests Run

### Backend targeted

`backend/venv/Scripts/python.exe -m unittest backend.tests.test_uat_user_provisioning backend.tests.test_local_login_session`

- 13 tests passed.
- Covered hashing/verification, complete provisioning, provisioned-user Login, safe environment, duplicate email, unauthorized role, and transaction rollback.

### Backend full regression

`backend/venv/Scripts/python.exe -m unittest discover -s backend/tests -p 'test_*.py'`

- 166 tests passed.

### Frontend

- `npm.cmd run lint` — passed.
- `npm.cmd test` — 16 tests passed, including provisioning form/payload/one-time credential assertions.
- `npm.cmd run build:local-dev` — passed; 2,406 modules transformed.
- Existing Vite large-chunk warning remains and is unrelated to provisioning.

## Follow-up Items

- Reset Password is deferred. It requires its own one-time credential and audit-safe action flow.
- Workspace column in the user table is deferred because the current list endpoint does not aggregate workspace ownership; it is not required for provisioning.
- Migrating the remaining Admin delete action to the shared ConfirmationDialog is deferred because delete semantics were intentionally untouched.
- Operational environments must apply migration 022 before using the endpoint.
- A later admin audit may add credential creation/reset timestamps without exposing password hashes.
