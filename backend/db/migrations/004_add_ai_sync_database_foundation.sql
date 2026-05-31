-- Database foundation for Google Sheet sync and AI transaction classification.
-- RLS is intentionally not enabled in this migration.

create extension if not exists pgcrypto;

create table if not exists schema_migrations (
  version text primary key,
  applied_at timestamptz not null default now()
);

create table if not exists google_oauth_connections (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null
    references workspaces (id)
    on delete cascade,
  user_id uuid not null
    references users (id)
    on delete cascade,
  google_email text,
  access_token_encrypted text,
  refresh_token_encrypted text,
  token_expiry timestamptz,
  scopes text[] not null default '{}',
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint google_oauth_connections_status_check
    check (status in ('active', 'disconnected', 'revoked', 'error'))
);

create table if not exists google_sheet_sources (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null
    references workspaces (id)
    on delete cascade,
  oauth_connection_id uuid
    references google_oauth_connections (id)
    on delete set null,
  sheet_id text not null,
  sheet_url text,
  sheet_name text,
  year int,
  status text not null default 'active',
  last_synced_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint google_sheet_sources_status_check
    check (status in ('active', 'disabled', 'error')),

  constraint google_sheet_sources_workspace_sheet_year_unique
    unique (workspace_id, sheet_id, year)
);

create table if not exists transactions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null
    references workspaces (id)
    on delete cascade,
  sheet_source_id uuid not null
    references google_sheet_sources (id)
    on delete cascade,
  external_row_key text not null,
  row_number int,
  transaction_date date,
  transaction_time timestamptz,
  title text not null,
  raw_category text,
  amount numeric(18, 2) not null,
  source_fund text,
  note text,
  direction text not null default 'expense',
  raw_payload jsonb not null default '{}'::jsonb,
  normalized_hash text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint transactions_direction_check
    check (direction in ('income', 'expense', 'saving_transfer', 'unknown')),

  constraint transactions_workspace_source_row_unique
    unique (workspace_id, sheet_source_id, external_row_key)
);

create table if not exists transaction_classifications (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null
    references workspaces (id)
    on delete cascade,
  transaction_id uuid not null
    references transactions (id)
    on delete cascade,
  allocation_type text not null,
  category_normalized text,
  confidence numeric(5, 4),
  reason text,
  model_provider text default 'google',
  model_name text,
  prompt_version text,
  schema_version text,
  status text not null default 'auto',
  is_current boolean not null default true,
  created_at timestamptz not null default now(),

  constraint transaction_classifications_allocation_type_check
    check (allocation_type in ('Needs', 'Wants', 'Savings')),

  constraint transaction_classifications_status_check
    check (status in ('auto', 'manual_override', 'needs_review'))
);

create table if not exists classification_rules (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null
    references workspaces (id)
    on delete cascade,
  match_type text not null,
  title_pattern text not null,
  raw_category_pattern text,
  allocation_type text not null,
  priority int not null default 100,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint classification_rules_match_type_check
    check (match_type in ('exact', 'contains', 'regex')),

  constraint classification_rules_allocation_type_check
    check (allocation_type in ('Needs', 'Wants', 'Savings'))
);

create table if not exists sync_jobs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null
    references workspaces (id)
    on delete cascade,
  sheet_source_id uuid
    references google_sheet_sources (id)
    on delete cascade,
  job_type text not null default 'google_sheet_sync',
  status text not null default 'queued',
  total_rows int default 0,
  inserted_rows int default 0,
  updated_rows int default 0,
  skipped_rows int default 0,
  failed_rows int default 0,
  error_message text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),

  constraint sync_jobs_job_type_check
    check (job_type in ('google_sheet_sync', 'classification', 'analytics_refresh')),

  constraint sync_jobs_status_check
    check (status in ('queued', 'running', 'success', 'failed', 'cancelled'))
);

create index if not exists google_oauth_connections_workspace_id_idx
  on google_oauth_connections (workspace_id);

create index if not exists google_oauth_connections_user_id_idx
  on google_oauth_connections (user_id);

create index if not exists google_sheet_sources_workspace_id_idx
  on google_sheet_sources (workspace_id);

create index if not exists google_sheet_sources_oauth_connection_id_idx
  on google_sheet_sources (oauth_connection_id);

create index if not exists transactions_workspace_id_idx
  on transactions (workspace_id);

create index if not exists transactions_sheet_source_id_idx
  on transactions (sheet_source_id);

create index if not exists transactions_transaction_date_idx
  on transactions (transaction_date);

create index if not exists transactions_source_fund_idx
  on transactions (source_fund);

create index if not exists transactions_normalized_hash_idx
  on transactions (normalized_hash);

create index if not exists transaction_classifications_workspace_id_idx
  on transaction_classifications (workspace_id);

create index if not exists transaction_classifications_transaction_id_idx
  on transaction_classifications (transaction_id);

create index if not exists transaction_classifications_allocation_type_idx
  on transaction_classifications (allocation_type);

create index if not exists transaction_classifications_is_current_idx
  on transaction_classifications (is_current);

create index if not exists classification_rules_workspace_id_idx
  on classification_rules (workspace_id);

create index if not exists classification_rules_is_active_idx
  on classification_rules (is_active);

create index if not exists sync_jobs_workspace_id_idx
  on sync_jobs (workspace_id);

create index if not exists sync_jobs_status_idx
  on sync_jobs (status);

create index if not exists sync_jobs_job_type_idx
  on sync_jobs (job_type);

create index if not exists sync_jobs_created_at_idx
  on sync_jobs (created_at);

drop trigger if exists set_google_oauth_connections_updated_at
  on google_oauth_connections;
create trigger set_google_oauth_connections_updated_at
before update on google_oauth_connections
for each row
execute function set_updated_at();

drop trigger if exists set_google_sheet_sources_updated_at
  on google_sheet_sources;
create trigger set_google_sheet_sources_updated_at
before update on google_sheet_sources
for each row
execute function set_updated_at();

drop trigger if exists set_transactions_updated_at
  on transactions;
create trigger set_transactions_updated_at
before update on transactions
for each row
execute function set_updated_at();

drop trigger if exists set_classification_rules_updated_at
  on classification_rules;
create trigger set_classification_rules_updated_at
before update on classification_rules
for each row
execute function set_updated_at();
