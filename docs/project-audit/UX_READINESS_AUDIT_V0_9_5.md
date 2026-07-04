# Omon Dashboard UX Readiness Audit

**Target:** v0.9.5 — UX Polish  
**Baseline:** v0.9.4 — UAT Safe Reset and Settings UX  
**Audit date:** 2026-07-05  
**Method:** Static frontend source audit; no application code changed

## Executive Summary

Omon has a sound UX foundation: state-aware dashboard onboarding, visible mutation progress, import delivery transparency, dirty-state protection, responsive alternatives in several data-heavy views, and clear Google Sheet reset guarantees.

The largest risks are:

1. The dashboard still shows `[Belum ada namanya]` and corrupted subtitle text; Login says `Finance AI` rather than Omon.
2. Blocking errors are often dead ends. The dashboard replaces the app with error text and no Retry; OAuth callback failure also has no recovery action.
3. English and Indonesian are mixed across navigation, labels, errors, and core verbs.
4. First-time setup is clear on Dashboard but fragmented in a long Settings page; draft settings and immediate integration actions can appear to share the same save model.
5. Confirmation patterns vary between strong custom reset dialogs, native `window.confirm`, and no confirmation for Google disconnect.
6. Mobile navigation can show six or seven destinations, while major import/admin tables rely on horizontal scrolling.
7. Dialog semantics exist, but focus trap, initial focus, Escape, and focus restoration are not evident.

**Readiness:** v0.9.5 should focus on coherence and recovery, not redesign. P1 work should repair dashboard trust, standardize language and state behavior, consistently protect destructive actions, and make Login → Connect → Add Source → Sync → Dashboard unmistakable.

## Audit Scope

Reviewed the React frontend under `apps/web/src`: Dashboard/analytics, Configuration, Google integration and sources, Blu PDF upload/review/history, Budgeting, Search, members/invitations, authentication, global navigation, shared state/modal/table/chart/card patterns, responsive utilities, and basic accessibility semantics.

This is source inspection, not browser/device or assistive-technology testing. APIs, schema, migrations, business logic, redesign, and new capabilities are outside scope.

## Current UX Strengths

- Dashboard onboarding distinguishes disconnected Google, missing source, and unsynced source states with relevant CTAs.
- Shared `EmptyState` supports explanation, actions, icon, compact mode, and touch-friendly buttons.
- Import separates upload, review, Omon persistence, Sheet delivery, partial delivery, and safe retry.
- Retry copy states that Sheet delivery retry does not recreate Omon transactions.
- Source/workspace reset dialogs define deleted data and explicitly protect the original Google Sheet.
- Settings protects unsaved changes with a persistent bar and leave-page dialog.
- Most mutations disable controls and show contextual progress.
- Search has intentional initial, loading, result, no-result, and detail states.
- Budget deletion copy explicitly protects transactions.
- Charts generally explain no data instead of showing blank canvases.

## Key UX Risks

### P1 — Must fix for v0.9.5

- Replace placeholder/corrupted branding and dashboard copy.
- Add Retry or safe alternate actions to blocking errors.
- Choose a primary UI language and normalize Save, Sync, Reset, Disconnect, Import, Review, Retry, Source, Sheet/Tab, Budget, Workspace, and Member.
- Unify destructive confirmations; confirm Google disconnect and clarify irreversible import rejection.
- Establish one canonical first-run path and visibly identify its next action.
- Separate draft configuration from immediate integration actions.
- Resolve mobile navigation capacity and critical dense-table usability.
- Complete keyboard/focus behavior for dialogs and menus.

### P2 — Before v1.0

- Establish shared loading, recoverable error, notification, and confirmation primitives.
- Add dashboard-level last-updated/last-synced context.
- Add actions to empty Review, History, Members, and Budget states.
- Replace technical login errors with user guidance.
- Add mobile-priority presentations to the largest tables.
- Standardize live-region, field-error, and success semantics.

### P3 — Nice to have

- Skeletons, richer empty illustrations, natural-language chart summaries, and reduced-motion-aware transitions.

## Page-by-Page Audit

### Dashboard

- **Empty — Good:** Strong setup state machine; charts/tables usually explain no data. Some actionable chart empties are plain text only.
- **Loading — Partial:** Initial state is plain full-screen `Loading Dashboard...`, without skeleton, retained context, or live status.
- **Error — Missing:** Full-page error has no Retry, Settings, or logout action. Secondary failures may collapse to empty data.
- **Success — Partial:** Refresh has no completion acknowledgement or freshness timestamp.
- **Confirmation — Not Applicable:** Read-only; dirty Settings navigation is protected upstream.
- **Copy/first-time — Missing/Good:** Setup CTAs are strong, but placeholder heading, corrupted subtitle, and mixed languages are release blockers.
- **Polish/responsive/accessibility — Partial:** Good grids and period filters; no last-updated context. Bottom nav is crowded and full-page states lack live semantics.
- **Priority:** P1.

### Configuration / Settings

- **Empty — Partial:** Source empty state has next steps; member/invitation empties are passive. `No workspace found` has no recovery.
- **Loading — Partial:** Connection, source, and insight sections expose progress, but patterns differ.
- **Error — Partial:** Visible, yet Retry is inconsistent outside the source list.
- **Success — Good:** Notifications cover saves, tests, syncs, resets, and invitations; generic configuration success should name the change.
- **Confirmation — Partial:** Excellent source/workspace reset and unsaved-change dialogs. Insight reset uses native confirm; disconnect is immediate.
- **Copy/first-time — Partial:** Numbered Connect/Add/Sync guide helps, but language mixing and the global Save bar blur draft versus immediate actions.
- **Responsive/accessibility — Partial:** Layout wraps and dialogs scale, but focus management and field-error association are incomplete.
- **Priority:** P1.

### Google Sheet Integration

- **Empty — Good:** Disconnected state explains the prerequisite.
- **Loading — Good:** Connect, disconnect, test, save, and sync expose progress and disable controls.
- **Error — Partial:** Failures are visible but recovery guidance varies.
- **Success — Good:** Connection/test/save/sync are distinct; sync includes row counts.
- **Confirmation — Partial:** Reset guarantees are excellent. Disconnect needs impact/preservation copy.
- **Copy/first-time — Partial/Good:** Three-step setup is coherent; terms/languages and immediate-action grouping need normalization.
- **Responsive/accessibility — Partial:** OAuth status/errors need consistent live and retry behavior.
- **Priority:** P1.

### Saved Google Sheet Sources

- **Empty/loading — Good:** Explains Add Source then Sync; list and row actions have contextual progress.
- **Error — Partial:** List has Refresh; some row failures lack adjacent recovery.
- **Success/confirmation — Good:** Save/sync/reset identify outcomes. Reset defines deleted Omon data, preserved original Sheet, and resync path.
- **Copy — Partial:** `source`, `spreadsheet`, `Google Sheet`, `sheet`, and `tab` need a glossary; UAT diagnostics may overwhelm normal users.
- **First-time — Good:** Test → Save → Sync is discoverable.
- **Responsive/accessibility — Partial:** Dense diagnostics/actions require device and keyboard testing.
- **Priority:** P1 for terminology/action clarity; P2 for diagnostics.

### Import / Blu PDF

- **Empty/loading/success — Good:** Names Blu support and unavailable providers, shows upload progress, and distinguishes review-ready from no-new-data.
- **Error — Partial:** Validation/server errors show; retry is implicit.
- **Confirmation — Not Applicable:** Upload creates a draft.
- **Copy — Partial:** English tabs/provider terms mix with Indonesian body copy.
- **First-time — Good:** Selection and transition to Review are direct.
- **Responsive/accessibility — Partial:** Layout and sizing are sound; keyboard/drop-zone and error announcement need runtime verification.
- **Priority:** P2, with terminology in P1.

### Import Review

- **Empty — Partial:** No active job says to upload but has no CTA; filtered empty lacks Clear Filter.
- **Loading/error/success — Good:** Contextual loading, targeted delivery failures, and clear Omon-save versus Sheet-delivery feedback.
- **Confirmation — Partial:** Bulk rejection needs reversibility/consequence clarity and confirmation if irreversible.
- **Copy — Partial:** `Setujui & Simpan di Omon` is strong. `Hapus Pilihan` means clear selection and sounds destructive.
- **First-time — Partial:** Add a short “what happens after approval” summary.
- **Responsive/accessibility — Partial:** `min-w-[860px]` table scrolls horizontally. Selection labels are good; focus/live results need testing.
- **Priority:** P1 for action copy/safety; P2 for mobile.

### Import History

- **Empty — Partial:** Clear, but no Upload CTA.
- **Loading/error/success — Good:** Initial, pagination, detail, refresh, retry, failure guidance, banners, and delivery counts are contextual.
- **Confirmation — Not Applicable:** Retry guarantee is explicit and nonduplicating.
- **Copy — Partial:** Safety wording is strong; labels mix languages.
- **First-time — Partial:** Empty state should route to Upload.
- **Responsive/accessibility — Partial:** `min-w-[1080px]` table scrolls; detail focus and retry announcement need verification.
- **Priority:** P2.

### Budgeting & Alerts

- **Empty — Good:** Distinguishes no budgets, future period, under-threshold, and no-chart-data states.
- **Loading/error/success — Partial:** Mutation progress exists, but initial loading, targeted Retry, and specific completion feedback lag behind Import/Settings.
- **Confirmation — Partial:** Copy protects transactions, but native dialogs are inconsistent.
- **Copy — Partial:** `budget`/`anggaran`, `alert`, and `Reset Budget` mix; reset actually deletes current-period budgets.
- **First-time — Partial:** Add a concise set-amount-then-save instruction.
- **Responsive/accessibility — Good/Partial:** Desktop/mobile row variants and labels exist; announcements need work.
- **Priority:** P1 for destructive language/confirmation; P2 for feedback.

### Search / Inquiry

- **Empty/loading — Good:** Examples, deliberate search loading, and detail loading are clear.
- **Error — Partial:** Validation is clear; `Search is not available` changes language and has no Retry.
- **Success/confirmation — Not Applicable:** Read-only result context is sufficient.
- **Copy — Partial:** Normalize errors and distinguish no match from service failure.
- **First-time — Good:** Examples make the feature approachable.
- **Responsive/accessibility — Partial:** Responsive grids exist; detail tables scroll. Loading is live, errors are not consistently announced.
- **Priority:** P2.

### Workspace Members

- **Empty/loading/error — Partial:** Passive empties, weak initial loading visibility, and manual retry.
- **Success — Good:** Invitation/cancellation identifies the affected email.
- **Confirmation — Partial:** Cancellation is immediate; confirm if it invalidates a sent link and explain resend behavior.
- **Copy/first-time — Partial:** Languages mix and role consequences should be summarized before sending.
- **Responsive/accessibility — Partial:** Rows wrap, but validation/errors need field association.
- **Priority:** P2.

### Authentication / Login

- **Empty/confirmation — Not Applicable.**
- **Loading — Good:** Password and callback flows show progress.
- **Error — Partial:** Invalid credentials are clear. Other messages expose `VITE_API_URL`, endpoint/backend/environment details; callback failure has no Return/Try Again.
- **Success — Good:** Direct transition is sufficient.
- **Copy/first-time — Partial:** `Finance AI` conflicts with Omon and languages mix; Google authorization purpose is unexplained.
- **Responsive/accessibility — Good/Partial:** Labels/autocomplete and single-column layout are good. Errors need alert semantics and focus.
- **Priority:** P1.

### Global Navigation / Sidebar

- **State feedback — Not Applicable** except contextual source/invitation status.
- **Copy/first-time — Partial:** Desktop/mobile labels vary; setup recommendation is not carried into navigation.
- **Responsive — Partial:** Desktop sidebar and mobile bar exist; six or seven equal destinations are dense on narrow phones.
- **Accessibility — Partial:** Labels/touch heights exist. Add `aria-current`; collapsed Settings must work by keyboard rather than hover alone.
- **Priority:** P1.

### Shared Components

- **Empty — Good/Partial:** Strong reusable component; actionable feature empties often bypass it.
- **Loading — Missing/Partial:** No shared primitive; patterns range from plain text to spinners.
- **Error — Missing:** No reusable recovery contract with Retry/alternate action.
- **Success — Partial:** Settings toast, import banners, and admin notices differ.
- **Modal/confirmation — Partial:** Custom roles exist, native confirm remains, focus management is incomplete.
- **Tables/charts/cards — Partial:** Usually legible with useful empties, but mobile treatment, accessible summaries, failure distinction, and freshness context vary.
- **Priority:** P1 for error/confirmation contracts; P2 for consolidation.

## UX Readiness Matrix

| Area | Empty State | Loading State | Error State | Success Feedback | Copywriting | Responsive | Priority |
|---|---|---|---|---|---|---|---|
| Dashboard | Good | Partial | Missing | Partial | Missing | Partial | P1 |
| Configuration / Settings | Partial | Partial | Partial | Good | Partial | Partial | P1 |
| Google Sheet Integration | Good | Good | Partial | Good | Partial | Partial | P1 |
| Saved Google Sheet Sources | Good | Good | Partial | Good | Partial | Partial | P1 |
| Import / Blu PDF | Good | Good | Partial | Good | Partial | Partial | P2 |
| Import Review | Partial | Good | Good | Good | Partial | Partial | P1 |
| Import History | Partial | Good | Good | Good | Partial | Partial | P2 |
| Budgeting & Alerts | Good | Partial | Partial | Partial | Partial | Good | P1 |
| Search / Inquiry | Good | Good | Partial | Not Applicable | Partial | Partial | P2 |
| Workspace Members | Partial | Partial | Partial | Good | Partial | Partial | P2 |
| Authentication / Login | Not Applicable | Good | Partial | Good | Partial | Good | P1 |
| Global Navigation / Sidebar | Not Applicable | Not Applicable | Not Applicable | Not Applicable | Partial | Partial | P1 |
| Shared Empty State | Good | Not Applicable | Not Applicable | Not Applicable | Good | Good | P2 |
| Shared Loading Pattern | Not Applicable | Missing | Not Applicable | Not Applicable | Partial | Partial | P2 |
| Shared Error Pattern | Not Applicable | Not Applicable | Missing | Not Applicable | Partial | Partial | P1 |
| Shared Toast / Banner | Not Applicable | Not Applicable | Partial | Partial | Partial | Good | P2 |
| Shared Modal / Confirmation | Not Applicable | Partial | Partial | Partial | Partial | Good | P1 |
| Shared Tables / Charts / Cards | Partial | Partial | Partial | Not Applicable | Partial | Partial | P2 |

## Prioritized Backlog for v0.9.5

### 1. Empty State Experience

**P1:** Add actions to dashboard blocking error, no-active-review, and filtered-empty review; ensure failed analytics cannot look like valid empty data.  
**P2:** Add Upload to empty History, Invite Member to member empty, and change-period/sync guidance to applicable chart empties. Use compact shared empty state when an action exists.  
**P3:** Optional illustrations after copy/actions stabilize.

### 2. Loading Experience

**P1:** Replace the dashboard's plain full-screen message with a branded, announced state; keep duplicate submission disabled for every immediate/destructive action.  
**P2:** Define page, section, table, and button loading variants; retain existing data during refresh and label it as updating.  
**P3:** Reduced-motion-aware transitions.

### 3. Copywriting Consistency

**P1:** Replace dashboard/login placeholders and mojibake; approve one language and glossary; rename `Hapus Pilihan`; rename budget reset to communicate deletion; remove infrastructure terms from user errors.  
**P2:** Normalize progress, empty, date/period, capitalization, and success language; simplify source diagnostics behind optional detail.  
**P3:** Add an editorial checklist to frontend reviews.

### 4. Feedback & Confirmation

**P1:** Create one danger confirmation pattern; replace native confirmation for budget/user/insight actions; confirm Google disconnect with exact preserved/affected scope; protect irreversible rejection; add Retry to dashboard and callback; retain Google Sheet safety guarantees.  
**P2:** Standardize notification/banner specificity, dismissal, duration, and live semantics; add specific budgeting success feedback; decide invitation-cancel behavior.  
**P3:** Optional diagnostic-detail links.

### 5. Dashboard Polish

**P1:** Ship approved heading/subheading; add `Last updated`/`Last synced`; distinguish failed from empty data.  
**P2:** Keep period/source context near values, add actionable chart empties, and normalize insight prose.  
**P3:** Card transitions and optional chart explanations.

### 6. First-Time User Readiness

**P1:** Present **Connect Google → Add URL → Test Connection → Save Source → Sync Now → View Dashboard** as the canonical path. Identify the next action after each step; separate draft Save Changes from immediate integration actions; provide callback recovery.  
**P2:** Explain Google authorization boundaries, member roles, and what happens after import approval.  
**P3:** Contextual tips only after v1.0; no tour/onboarding engine.

### 7. Mobile / Responsive Polish

**P1:** Test bottom navigation at 320/360/390/430 px; test dialogs with short height/software keyboard; prevent page-level horizontal overflow and unreachable primary actions.  
**P2:** Add priority-column/mobile-card views for review/history/admin tables; test long localization, source diagnostics, chart labels, notification stacking, landscape, and tablets.  
**P3:** Tune density after real-device feedback.

### 8. Accessibility Polish

**P1:** Add focus trap, initial focus, Escape, focus restoration, and title/description relationships to dialogs; `aria-current` to navigation; keyboard support to collapsed menus; appropriate alert/status announcements; non-color status cues.  
**P2:** Associate errors to fields, add chart summaries/table captions, verify focus/contrast/zoom/targets/screen-reader names, and respect reduced motion.  
**P3:** Formal WCAG 2.2 AA review before v1.0.

## Items Explicitly Deferred from v0.9.5

- Take a Tour
- Time-Aware System
- Merchant Normalization Engine
- New analytics, metrics, or chart types
- New database tables, migrations, APIs, or business logic
- New onboarding engine
- UI, navigation, or theme redesign
- New role/permission model
- P3 enhancements unless incidental and low-risk

## Recommended Implementation Order

1. Approve product name, interface language, dashboard copy, and glossary.
2. Define shared empty/loading/recoverable-error/notification/danger-confirmation contracts, including accessibility.
3. Fix Dashboard and first-run P1s: copy, error recovery, freshness, and failed-versus-empty distinction.
4. Separate draft settings from immediate integration actions.
5. Standardize destructive safety for disconnect, budgets, users, insight defaults, and rejection.
6. Polish Import selection copy, empties, approval consequences, and delivery announcements.
7. Normalize Budgeting, Search, Members, Login, and callback states.
8. Harden mobile navigation and dense tables.
9. Complete keyboard, focus, live-region, contrast, zoom, and screen-reader checks.
10. Run regression/UAT across first-time, destructive, and partial-failure paths.

## Testing Strategy for Future UX Polish

### State coverage

For every area test first load, retained-data refresh, slow response, no data/source/result, successful zero values, 4xx/401/5xx/network failure, successful mutation, duplicate-click prevention, partial success, long localized strings, missing optional values, and large values.

### Critical journeys

1. Password and Google login, including callback recovery.
2. New workspace through first successful dashboard sync.
3. Connected/no-source, saved/no-sync, failed sync, and successful resync.
4. PDF upload → review → approve → Omon save → Sheet success.
5. PDF approval → Omon save → Sheet partial/failure → safe retry.
6. Budget create/edit/delete/reset with unsaved-state and transaction-safety copy.
7. Member invite/cancel/accept/decline and role restrictions.
8. Source reset and factory reset with exact preservation guarantees.
9. Dirty Settings navigation through sidebar, bottom nav, workspace switch, and logout.

### Responsive and accessibility matrix

- Viewports: 320×568, 360×800, 390×844, 430×932, phone landscape, 768, 1024, 1280+; software keyboard open; 200% and 400% zoom/reflow.
- Check bottom-nav capacity, overflow, fixed controls, dialog height, tables, chart labels, diagnostics, notifications, and touch targets.
- Complete journeys keyboard-only; verify dialog/menu focus, Escape, and restoration.
- Test NVDA with Chrome/Firefox and VoiceOver/Safari when available.
- Run axe/Lighthouse, then manually check names, roles, order, contrast, non-color cues, chart alternatives, and reduced motion.

### Automation candidates

- Shared state and confirmation component variants.
- Dashboard onboarding copy/CTA per state.
- Destructive confirmations include affected scope and preservation guarantees.
- Settings dirty navigation choices.
- Import partial success and retry do not imply or create duplicate Omon records.
- Viewport tests for bottom navigation and dense-table alternatives.

### Release acceptance

- No P1 placeholder, mojibake, dead-end blocking error, or unconfirmed destructive action.
- Every first-run step has one clear next action.
- Every immediate action visibly reports progress and outcome.
- Empty and failed states are distinguishable.
- Google Sheet safety guarantees remain explicit.
- Core journeys pass keyboard and supported mobile viewport testing.

## Open Questions / Assumptions

1. Is v0.9.5 Indonesian-first, English-first, or formally bilingual? This audit assumes one primary UI language is preferable to ad hoc mixing.
2. What approved Omon title/subtitle should replace dashboard placeholders and `Finance AI`?
3. Does Google disconnect revoke OAuth only, while sources, Omon transactions, and configuration remain?
4. Can rejected draft rows be restored? This determines confirmation severity.
5. Does cancelling an invitation immediately invalidate it, and can it be resent safely?
6. Should dashboard freshness mean latest Google sync, import approval, or dashboard fetch? Label separate facts separately.
7. Is workspace creation guaranteed server-side? The UI can show `No workspace found` without a creation/recovery route.
8. Is 320 px CSS width the supported mobile floor?
9. This report assumes WCAG 2.2 AA is the v1.0 target, with critical dialog/keyboard/live-region issues in v0.9.5.
10. Findings are static. Runtime validation is required for computed layout, focus, timing, and screen-reader behavior.

## Conclusion

Omon does not need a redesign for v0.9.5. It needs consistent language, dependable state patterns, and disciplined recovery/safety behavior. Import and reset flows already demonstrate the desired standard: specific outcomes, explicit boundaries, and confidence-preserving copy. Applying that standard across Dashboard, authentication, Settings actions, Budgeting, navigation, and accessibility will make the release feel substantially complete without architectural or business-logic change.
