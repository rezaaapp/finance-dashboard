# Performance Audit

## Highest-Risk Paths

| Area | File / Function | Cause | Impact | Recommendation | Effort |
|---|---|---|---|---|---|
| Dashboard | `Dashboard.jsx::fetchDashboardData` | Up to 16 requests; most are sequential | Slow render and high DB load | Aggregate endpoint and parallel/cancel requests | 3–5 days |
| Analytics | `Dashboard.jsx` analytics effect | Re-fetches up to 8 datasets already requested | Duplicate load and stale state | Shared query cache/view model | 2–4 days |
| Analytics DB | `analytics_repository.py` | Repeated `extract(year/month...)` | Poor index use/full scans | Date ranges and plan tests | 2–4 days |
| Analytics DB | `analytics_repository.py` | Many independent aggregate queries | Repeated scans of transactions/classifications | Consolidated CTE/materialized aggregates | 5–10 days |
| Search | `inquiry_repository.py` | `%query%`, offset, second count query | Deep-page cost | Cursor pagination; optional count | 2–3 days |
| Import approve | `import_service.py` | Remote Google call during DB transaction | Pool starvation and lock duration | Outbox worker | 5–10 days |
| Import registry | fingerprint repository | One INSERT/UPSERT per fingerprint | Linear round trips | Batch `executemany`/set-based upsert | 1–2 days |
| Import history | import repository | Unbounded workspace history | Large payload/query | Cursor pagination | 1 day |
| Review | import repository | Unbounded drafts | Large response/render | Page/window review | 1–2 days |
| Transactions chart | analytics repository | Hard limit 500, no explicit pagination contract | Silent truncation/mismatch | Server aggregation or paged detail | 1–2 days |

## Cache and State

- Legacy Google Sheet finance service has in-process cache and stale-cache fallback.
- DB analytics has no shared cache visible.
- Frontend has no query library/cache; state is manually duplicated across views.
- Workspace and period changes do not consistently cancel in-flight Axios requests.
- Process-local cache/scheduler will diverge across replicas.

## Index Recommendations

Validate before adding:

- `(workspace_id, transaction_date)` already exists and should be used through range predicates.
- Search trigram index exists; verify `pg_trgm` and planner usage.
- Consider partial delivery index on `(workspace_id, import_job_id)` where sync status is retryable.
- Replace standalone low-cardinality indexes only after workload evidence.
- Add tenant-scoped fingerprint unique indexes as correctness constraints, not merely performance indexes.

## Required Verification

- Capture p50/p95 API latency and query count per dashboard load.
- Run `EXPLAIN (ANALYZE, BUFFERS)` for all analytics and inquiry queries on production-like volume.
- Load test 1,000 workspaces with concurrent dashboard reads and sync jobs.
- Measure connection pool exhaustion during Google API latency/failure.

