# Week 6 Workspace Switcher

## Behavior

Users can belong to more than one workspace. The web app lists the current
user's workspaces, stores the active workspace in local storage, and sends it
to the backend on workspace-aware API calls.

Local storage key:

```text
finance-dashboard-active-workspace-id
```

Request header:

```text
X-Workspace-Id: <workspace_id>
```

If the header is missing, backend endpoints fall back to the user's primary
workspace using the existing owner-first ordering. If the header is present but
the user is not a member of that workspace, the backend returns `403` with a
safe message.

## Backend API

`GET /api/workspaces`

Returns only workspaces where the current user is a member or owner:

```json
{
  "workspaces": [
    {
      "id": "e80daebe-cec5-4a5c-b1a8-70fedb8e68e7",
      "name": "Divya Koemala's Household",
      "role": "owner"
    },
    {
      "id": "9f11676e-90ca-4838-9c6a-e6ee2730b0d3",
      "name": "Reza Putra Pratama's Household",
      "role": "member"
    }
  ]
}
```

The backend validates active workspace access in:

- Dashboard and Analytics endpoints
- Dashboard available years
- Workspace configuration and members
- Google connection status
- Data sources and sync
- Sync jobs
- Classification endpoints
- Insight threshold settings

## Frontend

The header contains a workspace selector:

- One workspace: display the workspace name.
- Multiple workspaces: show a dropdown.
- Invalid saved workspace ID: fallback to the first workspace returned by the
  API.

Relevant API clients include `X-Workspace-Id` automatically:

- `dashboardApi.js`
- `googleSheetSourcesApi.js`
- `googleOAuthApi.js`
- `insightSettingsApi.js`
- `workspacesApi.js`

Workspace invitation APIs are documented in:

```text
docs/WEEK6_WORKSPACE_INVITATIONS.md
```

Switching workspace updates local storage and refetches Dashboard data.
Configuration is remounted for the active workspace so Google Sheet sources and
settings follow the selection.

## Existing Member Compatibility

Existing `workspace_members` rows are enough. A user does not need to accept a
new invitation if they are already a member.

Expected Divya scenario:

1. Divya logs in.
2. Workspace switcher shows `Divya Koemala's Household` and
   `Reza Putra Pratama's Household`.
3. Divya selects Reza workspace
   `9f11676e-90ca-4838-9c6a-e6ee2730b0d3`.
4. Dashboard, Analytics, Data Sources, and Settings read Reza workspace data.
5. Divya switches back to her own workspace and sees her own workspace data or
   onboarding/empty state.

## Manual QA

1. Login as `divyakoemala@gmail.com`.
2. Confirm both workspaces appear in the switcher.
3. Select `Reza Putra Pratama's Household`.
4. Confirm Dashboard shows Reza workspace data.
5. Open Analytics and confirm data follows Reza workspace.
6. Open Configuration and confirm Data Sources follow Reza workspace.
7. Select `Divya Koemala's Household`.
8. Confirm Dashboard changes to Divya workspace data or empty state.
9. Manually call an endpoint with a random `X-Workspace-Id`.
10. Confirm the backend returns `403 Workspace access denied`.

## Integration QA Notes

- Dashboard and Analytics endpoints resolve the workspace from
  `X-Workspace-Id` through backend membership validation.
- Data Sources, Google connection, Sync Jobs, Classifications, and Insight
  Settings use the same active workspace dependency.
- Missing `X-Workspace-Id` falls back to a workspace the user already belongs
  to; invalid `X-Workspace-Id` returns `403`.
- Switching workspace clears visible dashboard state, reloads available years,
  and refetches dashboard or analytics data without a browser refresh.
- Configuration is remounted per active workspace so Data Sources, Google
  connection status, insight settings, active members, and pending invitations
  are reloaded.

## Final Manual QA Checklist

Existing member compatibility:

1. Login as `divyakoemala@gmail.com`.
2. Confirm the switcher shows Divya and Reza workspaces.
3. Select Reza workspace and confirm Dashboard shows Reza data.
4. Select Divya workspace and confirm Dashboard shows Divya data or empty
   state.

Workspace isolation:

1. Send a request with a random `X-Workspace-Id`.
2. Confirm the backend returns `403 Workspace access denied`.
3. Confirm Data Sources, Settings, Classifications, Dashboard, and Analytics do
   not return data for inaccessible workspaces.

## Known Limitations

- Invitation acceptance flow now exists for new invitations. Existing active
  members still rely directly on `workspace_members`.
- Syncing a source still uses the current user's Google OAuth connection for
  the active workspace; members may need their own Google connection if they
  want to run sync actions.
- Static legacy token behavior still falls back to legacy/default handling
  where supported by existing routes.
