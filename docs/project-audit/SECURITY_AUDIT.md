# Security Audit

## Security Posture

Parameterized SQL and workspace membership checks are common strengths. Production blockers remain in legacy auth, workspace RBAC, browser token storage, tenant-less import constraints, file upload handling, and lack of database-level tenant enforcement.

## Findings

| Severity | Finding |
|---|---|
| Critical | Workspace configuration mutation checks global role instead of workspace role |
| Critical | Global import fingerprints allow cross-tenant interference |
| High | Shared static bearer token grants broad legacy/super-admin access |
| High | Seven-day JWT stored in localStorage; impersonator session also stored there |
| High | No upload size/signature/resource limits |
| High | Temp-file deletion does not enforce directory containment |
| High | No RLS/tenant policy defense in depth |
| Medium | Unverified ID-token claim fallback |
| Medium | No rate limiting found for login, OAuth start, invite, sync, import, or classification |
| Medium | No session revocation/token version/device management |
| Medium | OAuth connection state nonce is not persisted as consumed |
| Medium | No audit log for privileged/admin/workspace configuration mutations |
| Medium | CORS correctness depends entirely on deployment env |

## Environment Variable Names

Values were not copied.

Backend/database/auth:

```text
DATABASE_URL
SUPABASE_DATABASE_URL
DATABASE_MIGRATION_URL
SUPABASE_MIGRATION_DATABASE_URL
DATABASE_SSL
DATABASE_SSL_REJECT_UNAUTHORIZED
DATABASE_POOL_MAX
DATABASE_IDLE_TIMEOUT_MS
DATABASE_CONNECTION_TIMEOUT_MS
DASHBOARD_USERNAME
DASHBOARD_PASSWORD
DASHBOARD_AUTH_TOKEN
JWT_SECRET
JWT_EXPIRES_IN_MINUTES
TOKEN_ENCRYPTION_SECRET
TOKEN_ENCRYPTION_KEY
SUPER_ADMIN_EMAILS
CORS_ALLOWED_ORIGINS
USE_MOCK_DATA
```

Google and sync:

```text
GOOGLE_SHEET_ID
MAX_GOOGLE_SHEET_SOURCES
GOOGLE_SHEET_REGISTRY_JSON
GOOGLE_AUTH_MODE
GOOGLE_OAUTH_CLIENT_ID
GOOGLE_OAUTH_CLIENT_SECRET
GOOGLE_OAUTH_REDIRECT_URI
GOOGLE_LOGIN_REDIRECT_URI
GOOGLE_OAUTH_SCOPES
FRONTEND_URL
FRONTEND_AUTH_REDIRECT_URL
```

Classification/insights:

```text
AI_CLASSIFICATION_ENABLED
AI_PROVIDER
AI_MODEL
AI_ONLY_LOW_CONFIDENCE
AI_CONFIDENCE_THRESHOLD
AI_MAX_TRANSACTIONS_PER_RUN
INSIGHT_NEED_WARNING_RATIO
INSIGHT_NEED_DANGER_RATIO
INSIGHT_WANT_WARNING_RATIO
INSIGHT_WANT_DANGER_RATIO
INSIGHT_SAVING_WARNING_RATIO
INSIGHT_SAVING_GOOD_RATIO
INSIGHT_UNCATEGORIZED_WARNING_COUNT
INSIGHT_UNCATEGORIZED_DANGER_COUNT
INSIGHT_ANOMALY_WARNING_MULTIPLIER
INSIGHT_ANOMALY_DANGER_MULTIPLIER
```

Frontend:

```text
VITE_API_URL
VITE_API_BASE_URL
VITE_API_MODE
VITE_GUEST_MODE_MULTIPLIER
VITE_DASHBOARD_URL
```

## Recommended Security Gate

Before production:

1. Remove/disable shared-token auth in production.
2. Fix workspace-role authorization and add negative tests.
3. Tenant-scope import keys and mutations.
4. Add upload quotas and path containment.
5. Add rate limits.
6. Add short-lived/revocable sessions.
7. Add CSP and move session material away from localStorage.
8. Add RLS or equivalent restricted tenant DB policy.
9. Add immutable audit events for admin, invite, source, budget, and import actions.
10. Run SAST, dependency audit, secret scan, and authenticated penetration test.

