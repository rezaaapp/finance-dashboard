# Omon Dashboard v0.9.5 — UX Polish Sprint 1

## Background

Sprint 1 implements the highest-value findings from `UX_READINESS_AUDIT_V0_9_5.md` while preserving the v0.9.4 application architecture and behavior. The work is limited to user-facing copy, empty/loading/error states, confirmation consistency, accessibility details, and first-time path clarity.

No backend, API contract, database schema, migration, RBAC, Google authorization flow, Sheet synchronization logic, Blu PDF parsing/import logic, Import Transparency logic, or Safe Reset behavior was changed.

## Scope

- Establish the approved Omon Bahasa Indonesia modern copy direction.
- Improve critical Dashboard, Login, callback, Search, Import, member/source, and Budget states.
- Introduce one focused confirmation component rather than a broad modal system.
- Replace priority native/destructive confirmations for Disconnect, Anggaran, insight defaults, and Import rejection.
- Clarify the canonical first-run Sheet setup sequence.
- Preserve the intentionally temporary `Belum ada namanya` product identity.

## UX Audit References

Primary reference: `docs/project-audit/UX_READINESS_AUDIT_V0_9_5.md`.

Implemented P1 findings include Dashboard placeholder conflict cleanup (while retaining the approved temporary brand), blocking error recovery, Login identity conflict, developer-facing Login errors, mixed action copy, passive Import empties, ambiguous `Hapus Pilihan`, native priority confirmations, unconfirmed Google Disconnect, and incomplete confirmation keyboard behavior.

## Copywriting Decisions

- Created `docs/design/UX_COPYWRITING_GUIDELINE.md` as the permanent source of truth.
- Retained approved English actions and used Bahasa Indonesia for explanations, errors, toast content, confirmation, and empty states.
- Replaced `Finance AI` with `Belum ada namanya`.
- Retained the internal fun placeholder brand and replaced only its corrupted/conflicting subtitle with neutral copy.
- Changed Search action to `Cari Transaksi` and removed its English service error.
- Changed Import Review primary action to `Simpan ke Omon`, rejection to `Tolak`, and selection clearing to `Batalkan Pilihan`.
- Replaced user-facing `budget`/`expense` wording in newly touched empty/destructive states with `Anggaran`/`Pengeluaran`.
- Removed Login errors that exposed endpoint, environment, and backend terminology.

## Empty State Improvements

- Import Review without an active job now explains the prerequisite and offers `Upload PDF`.
- Filtered Review empty state explains that no matching transaction exists and offers `Clear Filter`.
- Import History empty state explains how history is created and offers `Upload PDF`.
- Saved source empty copy now presents Add URL → Test Connection → Save Source → Sync Now.
- Workspace member and pending-invitation empty copy is clearer and action-oriented through the existing invite form.
- Anggaran empty copy explains that users can add an amount in the form above.

## Error and Loading Improvements

- Dashboard initial loading is now branded, contextual, and announced as status.
- Dashboard blocking errors are human-readable and offer `Coba Lagi`, `Buka Settings`, and `Logout`.
- Login infrastructure errors now provide safe user guidance.
- Google callback failure offers `Kembali ke Login`.
- Search unavailability is expressed in Indonesian with a clear retry suggestion and alert semantics.
- Existing retained-data refresh behavior was preserved where already implemented; no data-loading logic changed.

## Confirmation Improvements

- Added a focused `ConfirmationDialog` with affected/safe sections, initial focus, Escape handling, Tab focus containment, and focus restoration.
- Google Disconnect now confirms lost access/sync capability and explicitly preserves Omon data, original Sheet, source, and workspace configuration.
- Single/all Anggaran deletion now uses the custom confirmation and protects transactions, Google Sheet, and other periods in copy.
- Insight default reset now explains that values are loaded into the draft and require `Save Changes`.
- Import bulk rejection now explains that selected rows leave the Review and are not saved to Omon or sent to the Sheet.
- Existing Reset Synced Data safety semantics were preserved.

## First-Time User Path Improvements

The integration empty/setup copy now reinforces:

`Login → Connect Google → Add Spreadsheet URL → Test Connection → Save Source → Sync Now → View Dashboard`

The global `Save Changes` copy is reserved for configuration drafts, while integration actions remain immediate. The dirty-state bar now explains the draft state in Bahasa Indonesia.

## Files Changed

- `apps/web/src/components/ConfirmationDialog.jsx`
- `apps/web/src/components/import/ImportHistory.jsx`
- `apps/web/src/components/import/ImportReview.jsx`
- `apps/web/src/pages/BudgetingAlerts.jsx`
- `apps/web/src/pages/Configuration.jsx`
- `apps/web/src/pages/Dashboard.jsx`
- `apps/web/src/pages/GoogleAuthCallback.jsx`
- `apps/web/src/pages/ImportTransactions.jsx`
- `apps/web/src/pages/Login.jsx`
- `apps/web/src/pages/Search.jsx`
- `docs/design/UX_COPYWRITING_GUIDELINE.md`
- `docs/project-audit/UX_POLISH_V0_9_5_SPRINT_1.md`

## Tests Run

- `npm.cmd run lint` — passed.
- `npm.cmd test` — passed, 4/4 frontend utility tests.
- `npm.cmd run build` — environment validation correctly blocked the build because the current production API URL points to localhost.
- `npm.cmd run build:local-dev` — passed; Vite transformed 2,405 modules and produced the frontend bundle.
- Backend tests — not run because no backend code or behavior changed.

The local build retains the existing large-chunk warning; it is unrelated to this UX-only sprint.

## Regression Notes

- No API calls, payload shapes, routing model, authorization decisions, or persistence behavior changed.
- Disconnect still calls the existing disconnect operation only after explicit confirmation.
- Anggaran deletion still calls the same single/period deletion functions.
- Import approval/rejection payloads are unchanged; confirmation only gates the existing rejection action.
- Reset Synced Data and factory reset handlers were not altered.
- The confirmation component prevents duplicate action through existing loading flags.

## Deferred Items

- Exhaustive copy normalization in admin/developer-only surfaces.
- Replacing the remaining Admin User native delete confirmation.
- A broad modal/toast/loading design system.
- Mobile card redesign for the largest tables.
- Final product branding and landing page.
- Last-synced Dashboard metadata, which requires a confirmed product definition of freshness.
- Take a Tour, onboarding engine, Time-Aware System, Merchant Normalization, new analytics, theme redesign, schema/migration/API/RBAC changes.

## Unresolved UX Decisions

1. Confirm whether Import rejection can be restored through any supported workflow. Current copy promises only that rejected rows leave the current Review and are not persisted/delivered.
2. Define whether Dashboard `Last updated` should mean latest Sheet sync, latest Import approval, or latest Dashboard fetch.
3. Decide whether Admin User deletion joins the shared confirmation in a later admin-focused sprint.
4. Final branding remains intentionally deferred; `Belum ada namanya` is the only temporary identity shown.
