# UAT Safe Data Reset Improvements

## Problem Found During UAT

The Google Sheet source card placed an ambiguous **Delete** action beside **Sync Now**. It was not clear whether the action removed the source, Omon data, or the original spreadsheet. UAT also needed a repeatable way to return a development workspace to a clean operational state without removing identity and integration configuration.

## P1 — Reset Synced Data

`POST /api/data-sources/{source_id}/reset-synced-data` deletes only rows from `transactions` matching all of:

- the active `workspace_id`;
- the selected `sheet_source_id`;
- `source_origin = 'google_sheet'`.

The source is resolved through the existing workspace-scoped authorization path. Transaction classifications are removed by the existing transaction foreign-key cascade. Blu PDF and future/manual non-Google-Sheet rows remain.

The UI now uses **Reset Synced Data** and an explicit confirmation modal. It guarantees that the original Google Sheet is neither deleted nor modified and explains that Sync Now can be used again.

Preserved: Google OAuth connection/tokens, Google Sheet source, selected tabs/default tab configuration, workspace configuration, users, workspace, and memberships.

## P2 — Factory Reset Workspace Data

`POST /api/workspace/factory-reset-data` is available only in `local-dev` and only to a workspace owner or global super admin. All deletes execute inside one database transaction in dependency-safe order.

Deleted entities:

- `transactions` (transaction classifications cascade);
- `import_jobs` (import drafts cascade);
- `import_transaction_registry`;
- `budgets`;
- `budget_category_ignores`;
- `sync_jobs`.

Preserved entities:

- `users`, `workspaces`, and `workspace_members`;
- `google_oauth_connections`;
- `google_sheet_sources` and `workspace_configurations`;
- classification rules and workspace insight configuration;
- migration tracking and catalog/configuration data.

No endpoint or service calls the Google Sheets API. Original spreadsheet content is never modified.

## Test Summary

Coverage verifies source/workspace/origin filtering, preservation by omission, cross-workspace rejection, production and unauthorized access blocking, transactional rollback propagation, and the ability to sync again because source/OAuth configuration remains.
