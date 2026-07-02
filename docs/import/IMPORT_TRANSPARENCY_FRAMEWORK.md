# Import Transparency Framework

## Architecture

Importers return a backward-compatible summary plus presentation-safe detail rows. Google Sheets is the first adapter; the contract excludes database IDs and fingerprint implementation so Blu PDF, MyBCA, CSV, and future importers can reuse it.

Multi-sheet preferences use the existing `workspace_configurations.google_sheet_sources` JSONB metadata. No schema migration is required. Legacy `google_sheet_sources.sheet_name` remains the fallback when `selected_tabs` is absent.

## Response Contract

Existing `inserted_rows`, `updated_rows`, `skipped_rows`, and `failed_rows` fields remain. Additive fields are `summary` and `details`, where details contains `inserted`, `updated`, `skipped`, and `failed` arrays. Each row exposes only `sheet_name`, `date`, `merchant`, `amount`, `owner`, `status`, and `reason`.

Each status is limited to 500 detail rows. UUIDs, fingerprints, source IDs, SQL errors, and stack traces are never exposed.

## Reason Taxonomy

- `IMPORTED`: inserted successfully.
- `UPDATED`: existing transaction updated successfully.
- `DUPLICATE_BATCH`: duplicate in the current payload.
- `ALREADY_IMPORTED`: unchanged row imported previously.
- `EXISTING_TRANSACTION`: transaction already exists in the workspace.
- `VALIDATION_FAILED`: normalization or validation failed.
- `DATABASE_WRITE_FAILED`: persistence failed after validation.
- `UNKNOWN`: no user-actionable reason applies.

The frontend maps these codes to human-readable labels.

## Import Result Flow

The importer classifies outcomes using already-loaded payload and batch lookup data. The UI shows **View Details** when any counter is non-zero, with status tabs, a desktop table, and compact mobile cards.

## Multi Sheet Sync Flow

Connection testing returns valid transaction tabs. Users select individual months or Select All. Sync processes only persisted `selected_tabs` and reports processed, skipped, and failed tabs. Sources without `selected_tabs` continue using their legacy default tab.

## Future Extensibility

New importers map native outcomes to this detail shape and taxonomy, batch-load existing identities, avoid per-row queries, and enforce the 500-row-per-status cap.
