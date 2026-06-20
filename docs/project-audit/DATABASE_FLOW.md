# Database Flow Audit

## Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ WORKSPACE_MEMBERS : joins
    WORKSPACES ||--o{ WORKSPACE_MEMBERS : contains
    WORKSPACES ||--|| WORKSPACE_CONFIGURATIONS : configures
    USERS ||--o| USER_TOKENS : owns
    WORKSPACES ||--o{ GOOGLE_OAUTH_CONNECTIONS : authorizes
    USERS ||--o{ GOOGLE_OAUTH_CONNECTIONS : connects
    GOOGLE_OAUTH_CONNECTIONS ||--o{ GOOGLE_SHEET_SOURCES : grants_access
    WORKSPACES ||--o{ GOOGLE_SHEET_SOURCES : owns
    WORKSPACES ||--o{ TRANSACTIONS : owns
    GOOGLE_SHEET_SOURCES ||--o{ TRANSACTIONS : sources
    TRANSACTIONS ||--o{ TRANSACTION_CLASSIFICATIONS : classified_as
    WORKSPACES ||--o{ CLASSIFICATION_RULES : defines
    WORKSPACES ||--o{ SYNC_JOBS : runs
    GOOGLE_SHEET_SOURCES ||--o{ SYNC_JOBS : syncs
    WORKSPACES ||--o| WORKSPACE_INSIGHT_SETTINGS : configures
    WORKSPACES ||--o{ WORKSPACE_INVITATIONS : invites
    USERS ||--o{ WORKSPACE_INVITATIONS : sends_or_receives
    WORKSPACES ||--o{ BUDGETS : budgets
    WORKSPACES ||--o{ BUDGET_CATEGORY_IGNORES : ignores
    WORKSPACES ||--o{ IMPORT_JOBS : imports
    IMPORT_JOBS ||--o{ IMPORT_DRAFT_TRANSACTIONS : stages
    IMPORT_JOBS ||--o{ TRANSACTIONS : creates

    USERS {
      uuid id PK
      citext email UK
    }
    WORKSPACES {
      uuid id PK
      text subscription_status
    }
    WORKSPACE_MEMBERS {
      uuid id PK
      uuid workspace_id FK
      uuid user_id FK
      text role
    }
    GOOGLE_SHEET_SOURCES {
      uuid id PK
      uuid workspace_id FK
      uuid oauth_connection_id FK
      text sheet_id
      int year
    }
    TRANSACTIONS {
      uuid id PK
      uuid workspace_id FK
      uuid sheet_source_id FK
      uuid import_job_id FK
      text import_transaction_fingerprint
      text canonical_fingerprint
    }
    IMPORT_JOBS {
      uuid id PK
      uuid workspace_id FK
      text status
      text temp_file_path
    }
    IMPORT_DRAFT_TRANSACTIONS {
      uuid id PK
      uuid import_job_id FK
      text datetime
      text transaction_fingerprint
    }
    IMPORT_TRANSACTION_REGISTRY {
      text transaction_fingerprint PK
      text provider
      text status
    }
```

`IMPORT_TRANSACTION_REGISTRY` intentionally appears disconnected because the schema has no workspace or transaction FK. This is a Critical defect for multi-tenant use.

## Source-of-Truth Classification

| Data | Role |
|---|---|
| `transactions` | Final ledger/source of truth for dashboard analytics |
| `import_draft_transactions` | Temporary review staging |
| `import_jobs` | Import lifecycle/history |
| `import_transaction_registry` | Duplicate suppression registry; currently unsafe globally |
| Google Sheets | Input source for sync and delivery projection for Smart Import |
| `transaction_classifications` | Current and historical classification state |
| `budgets` | Workspace monthly category budget |

## Constraint and Index Findings

- Good: workspace FKs, cascade rules, workspace-aware transaction uniqueness for sheet rows, budget period checks, current-classification uniqueness.
- Critical: import fingerprint uniqueness omits workspace.
- High: canonical unique index may be skipped silently if duplicates exist.
- High: duplicate numeric migration prefixes.
- Medium: category uniqueness is case-sensitive.
- Medium: `import_draft_transactions.datetime` is text.
- Medium: standalone indexes on low-cardinality status/boolean columns may add write cost with limited selectivity.
- Medium: no FK from registry to workspace/job/transaction.
- Medium: no RLS policies found in migrations.
- Need Verification: actual production indexes, constraints, duplicate counts, orphan counts, table bloat, and query plans.

## Required Pre-Production SQL Audit

Run in staging before repair:

```sql
select import_transaction_fingerprint, count(*), count(distinct workspace_id)
from transactions
where import_transaction_fingerprint is not null
group by 1
having count(*) > 1 or count(distinct workspace_id) > 1;

select canonical_fingerprint, count(*), count(distinct workspace_id)
from transactions
where canonical_fingerprint is not null
group by 1
having count(*) > 1 or count(distinct workspace_id) > 1;

select table_name
from information_schema.tables
where table_schema = 'public'
order by table_name;
```

