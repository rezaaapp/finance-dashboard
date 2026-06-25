# UAT-CLOSURE-001 — Final UAT Closure Report

Date: 2026-06-25  
Branch: `uat/local-postgres-stabilization`  
Workspace: `Admin's Household`  
Workspace ID: `37cba4df-0935-44a2-b3e3-41e4c332aa14`

## Executive summary

Local PostgreSQL UAT stabilization, Blu PDF import, Google Sheet integration, and Reza + Divya private-alpha workspace validation are complete.

Final recommendation:

- Reza-only usage: READY.
- Reza + Divya private alpha: READY with notes.
- 5 beta users: NOT YET.
- Public production: NOT YET.

The product is now usable for the intended private-alpha household workflow where PostgreSQL/Omon is the source of truth and Google Sheets is a projection/export layer. Broader beta and public production still need hardening around onboarding, role policy, UX polish, operational monitoring, and multi-user/multi-workspace edge cases.

## Completed UAT phases

| UAT area | Status | Notes |
|---|---:|---|
| Local PostgreSQL reset and migration validation | PASS | Local DB reset completed; migrations 22/22 valid; migration 019 validated. |
| Minimal workspace seed | PASS | Seed is valid and idempotent. |
| Empty-state regression | PASS | No loading loop, NaN, or render crash in empty states. |
| Blu PDF upload/parsing | PASS | Blu PDF parsed successfully. |
| Import review/approval/reject lifecycle | PASS | 36 Blu transactions reviewed; 25 approved and 11 rejected. |
| Local-first approval without Google Sheet | PASS | Ledger persistence no longer blocked by missing spreadsheet/OAuth. |
| Category bootstrap fallback | PASS | Fresh workspace receives default category options. |
| Reopen existing review job | PASS | Existing review jobs can be resumed after reload. |
| Duplicate/reupload handling | PASS | No duplicate final transaction; no-new import state validated. |
| Editable transaction name in import review | PASS | Edited title is persisted and searchable. |
| Dashboard consistency | PASS | Dashboard totals match PostgreSQL. |
| Search consistency | PASS | Blu transactions are indexed and searchable. |
| Analytics consistency | PASS | Analytics matches PostgreSQL/Dashboard/Search totals. |
| Budgeting & alerts | PASS | Create/edit/reset behavior validated; calculations stable. |
| Google OAuth connect/disconnect/reconnect | PASS | OAuth lifecycle validated locally. |
| Google token refresh | PASS | Expired access tokens refresh using stored refresh token. |
| Default destination sheet persistence | PASS | `sheet_name` persists and defaults into sync flows. |
| Google Sheet metadata validation | PASS | Dropdown metadata readable after sheet setup. |
| Single spreadsheet delivery | PASS | One transaction delivered with correct A–G mapping. |
| Datetime formatting | PASS | Column B displays human-readable datetime. |
| Controlled bulk delivery | PASS | Remaining pending approved transactions delivered without duplicates. |
| Completed-state retry | PASS | Retry after all delivered is idempotent. |
| Workspace/member setup | PASS | Admin owner, Reza member, Divya member configured. |
| Workspace isolation | PASS | Members can access shared workspace; non-member is blocked. |
| Member dashboard transaction access | PASS | Divya can read workspace transaction endpoints. |
| Owner filter validation | PASS | Reza/Divya owner filters validated with positive Divya evidence. |

## Final database evidence

Current local PostgreSQL state after controlled Divya-owned UAT transaction:

| Metric | Value |
|---|---:|
| Final transactions | 26 |
| Total expense | Rp1.877.169 |
| Reza transactions | 25 |
| Reza total | Rp1.867.169 |
| Divya transactions | 1 |
| Divya total | Rp10.000 |
| Import registry approved | 25 |
| Import registry rejected | 11 |
| Transaction sync success | 25 |
| Transaction sync pending | 1 |

The pending transaction is intentional manual UAT evidence:

- ID: `81b9cb8e-3432-455a-a07b-0260288057c2`
- Title: `UAT Divya Test Transaction`
- Owner: `Divya`
- Date: `2026-06-10`
- Category: `Food`
- Amount: Rp10.000
- Source fund: `BCA`
- Sync status: `pending`
- Source reference: `UAT-WORKSPACE-005 manual local evidence`

The original Blu PDF import evidence remains intact:

- Approved final transactions: 25
- Approved registry rows: 25
- Rejected registry rows: 11
- Google-delivered approved transactions: 25

## Google integration state

| Area | State |
|---|---|
| Google OAuth | Connected and refresh-capable |
| Spreadsheet | `Omon-UAT-Spreadsheet` |
| Destination sheet | `Start 1 Juni` |
| Delivered approved transactions | 25 |
| Pending manual UAT transaction | 1 |
| Completed-state retry | PASS / idempotent |
| Dropdown validation metadata | Readable for Nama, Kategori, Source Dana |
| Source Dana casing | Validated against dropdown where metadata is available |
| Datetime display | Human-readable format validated |

Google Sheets remains a projection layer. Ledger integrity did not depend on spreadsheet availability.

## Member state

| User | Email | Workspace role |
|---|---|---|
| Admin | `admin@local.finance-dashboard` | owner |
| Reza | `rezaaapp@gmail.com` | member |
| Divya | `divyakoemala@gmail.com` | member |

Validated behavior:

- Admin can access `Admin's Household`.
- Google Reza can access `Admin's Household`.
- Divya can access `Admin's Household`.
- Non-member receives `403 Workspace access denied`.
- Google source remains workspace-scoped.
- Import history/detail remains workspace-scoped.

## Owner filter validation

Owner-positive path was validated by adding one controlled local UAT transaction for Divya.

Results:

| Endpoint / area | All | Reza | Divya | Status |
|---|---:|---:|---:|---|
| Dashboard transactions | 26 / Rp1.877.169 | 25 / Rp1.867.169 | 1 / Rp10.000 | PASS |
| Monthly allocation | Rp1.877.169 | Rp1.867.169 | Rp10.000 | PASS |
| Category heatmap | workspace data | Reza data | Food / Rp10.000 | PASS |
| Category trends | workspace data | Reza data | Food / Rp10.000 | PASS |
| Source Dana analytics | workspace data | Reza data | BCA / Rp10.000 | PASS |
| Grocery vs Food | workspace data | Reza data | Makanan / Rp10.000 | PASS |
| Non-member access | blocked | blocked | blocked | PASS |

## Commit list for stabilization work

Key commits in this phase:

- `b4270ab` — `fix(import): allow local-first approval without spreadsheet`
- `7b75968` — `fix(import): add category bootstrap for fresh workspace`
- `d8c0068` — `fix(import): reopen existing review jobs`
- `d270ea2` — `fix(import): harden duplicate reupload handling`
- `c500cf7` — `fix(import): allow editing transaction name during review`
- `dac2837` — `fix(search): index Blu transactions for inquiry`
- `cf5a645` — `fix(budget): make budget edits explicit and persistent`
- `7374ae6` — `docs(uat): finalize local postgres stabilization report`
- `a466068` — `fix(sync): persist default destination sheet`
- `72bd027` — `fix(sync): refresh expired Google access token automatically`
- `f79a80f` — `fix(sync): apply explicit datetime formatting for spreadsheet delivery`
- `8035082` — `fix(workspace): allow members to read dashboard transactions`
- `a3da02b` — `fix(analytics): apply owner filter to monthly allocation`

## Bugs fixed

| Bug ID / area | Severity | Status |
|---|---:|---|
| UAT-IMPORT-001 — Fresh workspace category options empty | High | Fixed |
| UAT-IMPORT-002 — Approval blocked by Google Sheet dependency | High | Fixed |
| UAT-IMPORT-003 — Existing review job not reopenable | High | Fixed |
| UAT-PDF-002 — Duplicate/reupload stale draft handling | High | Fixed |
| UAT-DATA-001 — Transaction title not editable during review | Medium | Fixed |
| UAT-SEARCH-001A — Blu transactions missing search index | High | Fixed |
| UAT-BUDGET-001A — Budget edit not persisted / misleading save UX | High | Fixed |
| UAT-GS-001A — Default destination tab not persisted | Medium | Fixed |
| UAT-GS-002A — Spreadsheet datetime displays as serial | Medium | Fixed |
| UAT-GS-003 — Expired Google access token causes 401 | High | Fixed |
| UAT-WORKSPACE-003 — Member blocked by premium role guard | High | Fixed |
| UAT-WORKSPACE-004A — Monthly allocation ignores owner filter | High | Fixed |

## Remaining product gaps

These are not blockers for Reza + Divya private alpha, but they block broader beta/public production.

### Medium

- Search has no explicit owner filter.
  - Current Search is workspace-level and can find the Divya UAT transaction by keyword.
  - Recommendation: add owner filter when Search becomes part of multi-user beta.

- Budgeting is workspace-level, not owner-level.
  - Current behavior is acceptable for shared household budgeting.
  - Recommendation: clarify product decision before adding owner-scoped budgets.

- Some dashboard endpoints remain intentionally global or view-model scoped.
  - Owner-aware analytics endpoints were validated.
  - Recommendation: audit every chart/widget when owner filter is exposed more broadly in the UI.

- Google missing/renamed destination sheet recovery needs stronger UX.
  - Completed-state retry is idempotent.
  - Recommendation: improve user-facing guidance for renamed/missing tabs before wider beta.

### Low

- Branding placeholder remains out of scope.
- Copy still references spreadsheet-centric wording in some areas.
- Test runner has known environment noise from local PowerShell Conda profile.
- Full backend discovery currently has unrelated `httpx.post` test harness errors in Google token tests under this local environment.

## Production readiness recommendation

### Reza-only

READY.

Reason:

- Local ledger flow is stable.
- Import, dashboard, search, analytics, budgeting, and Google sync have passed UAT.
- Reza-only usage does not depend on broader member/role edge cases.

### Reza + Divya private alpha

READY with notes.

Reason:

- Admin/Reza/Divya membership is configured.
- Divya can access shared workspace.
- Non-member is blocked.
- Owner filters now validate both Reza and Divya positive paths.
- One Divya-owned transaction exists as local UAT evidence.

Notes:

- Search is still workspace-level, not owner-filtered.
- Budgeting is workspace-level, not owner-filtered.
- The Divya manual UAT transaction is pending Google sync by design and should not be delivered unless explicitly requested.

### 5 beta users

NOT YET.

Blockers:

- Need broader multi-user onboarding and invitation UAT.
- Need explicit owner filter UX across Search and all exposed analytics widgets.
- Need role policy review for owner/member/admin capabilities.
- Need operational monitoring and clearer error recovery flows.
- Need more cross-workspace and non-member endpoint coverage.

### Public production

NOT YET.

Blockers:

- Supabase production has not been used in this stabilization phase and must not be assumed equivalent.
- Need production environment verification, secrets review, backup/recovery plan, and monitoring.
- Need public-facing auth/session hardening review.
- Need stronger Google error UX for disconnected/renamed/missing sheet states.
- Need load/performance smoke testing beyond local UAT.
- Need final security review for workspace isolation at production scale.

## Final closure

Local PostgreSQL + Google Integration + Workspace Private Alpha readiness is closed as PASS for the intended private-alpha scope.

Next recommended phase:

1. Continue Reza + Divya private alpha using `Admin's Household`.
2. Observe real usage for owner filter, budgeting, search, and Google sync.
3. Do not open broader beta until owner-filter UX, onboarding, production environment checks, and monitoring are completed.
