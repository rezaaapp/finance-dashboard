# Stabilization Roadmap

## Sprint 0 — Freeze, Measure, Protect

- [ ] Freeze new import providers and schema features.
- [ ] Audit existing fingerprints across workspaces.
- [ ] Decide canonical tenant-scoped identity.
- [ ] Repair global registry and unique indexes.
- [ ] Fix workspace configuration RBAC.
- [ ] Add negative cross-workspace tests.
- [ ] Document PostgreSQL as source of truth.

## Sprint 1 — Critical Safety

- [ ] Introduce outbox/idempotent spreadsheet delivery.
- [ ] Remove static auth from production.
- [ ] Add upload size/type/page limits.
- [ ] Add temp-path containment and object-storage plan.
- [ ] Add mutation idempotency keys.
- [ ] Add rate limits to high-risk endpoints.

## Sprint 2 — Performance

- [ ] Add dashboard and analytics view-model endpoints.
- [ ] Convert date extraction filters to ranges.
- [ ] Add import/history cursor pagination.
- [ ] Add frontend request cancellation and query cache.
- [ ] Verify query plans on production-like data.

## Sprint 3 — UX and Product Semantics

- [ ] Explain auto-registration via Google.
- [ ] Make workspace selection explicit.
- [ ] Add invitation email delivery and expiry.
- [ ] Separate “approved in Omon” from “delivered to Sheet”.
- [ ] Add widget-level errors/retries.
- [ ] Complete accessibility and responsive audit.

## Sprint 4 — Modularization

- [ ] Split dashboard, configuration, import service, and analytics repository.
- [ ] Centralize API client/auth handling.
- [ ] Centralize workspace policy.
- [ ] Move cleanup/sync/classification to durable workers.
- [ ] Add structured logs, trace IDs, metrics, and audit events.

## Sprint 5 — Verification

- [ ] Auth/session tests.
- [ ] Workspace RBAC matrix tests.
- [ ] Tenant isolation tests.
- [ ] Import concurrency/idempotency tests.
- [ ] Analytics contract and SQL comparator tests.
- [ ] Budget normalization tests.
- [ ] Browser E2E for login, switch, invite, sync, import, retry, and logout.
- [ ] Load, failure-injection, and security testing.

## Release Gate

Production release requires:

- No open Critical findings.
- Cross-workspace isolation tests passing.
- DB/Sheet mismatch recovery tested.
- Migration applied on a clean and a realistic existing database.
- Backend tests executable in CI.
- Frontend lint/build and backend tests passing.
- Staging smoke test completed with production-like OAuth and database settings.

