-- Scope Smart Import identity and duplicate protection by workspace.
--
-- Historical registry rows do not contain tenant provenance. Rows that can be
-- linked to an imported transaction are backfilled. Unresolved rows are
-- archived instead of being guessed or applied to every workspace.

create table if not exists public.legacy_unscoped_import_transaction_registry (
  transaction_fingerprint text primary key,
  provider text not null,
  status text not null,
  created_at timestamptz not null,
  approved_at timestamptz,
  rejected_at timestamptz,
  last_seen_at timestamptz not null,
  archived_at timestamptz not null default now(),
  archive_reason text not null
);

alter table public.import_transaction_registry
  add column if not exists workspace_id uuid
    references public.workspaces(id)
    on delete cascade;

with resolved_registry_workspaces as (
  select
    import_transaction_fingerprint as transaction_fingerprint,
    min(workspace_id::text)::uuid as workspace_id
  from public.transactions
  where import_transaction_fingerprint is not null
  group by import_transaction_fingerprint
  having count(distinct workspace_id) = 1
)
update public.import_transaction_registry registry
set workspace_id = resolved.workspace_id
from resolved_registry_workspaces resolved
where registry.workspace_id is null
  and registry.transaction_fingerprint = resolved.transaction_fingerprint;

insert into public.legacy_unscoped_import_transaction_registry (
  transaction_fingerprint,
  provider,
  status,
  created_at,
  approved_at,
  rejected_at,
  last_seen_at,
  archive_reason
)
select
  transaction_fingerprint,
  provider,
  status,
  created_at,
  approved_at,
  rejected_at,
  last_seen_at,
  'workspace provenance unavailable during migration 019'
from public.import_transaction_registry
where workspace_id is null
on conflict (transaction_fingerprint)
do nothing;

delete from public.import_transaction_registry
where workspace_id is null;

alter table public.import_transaction_registry
  alter column workspace_id set not null;

alter table public.import_transaction_registry
  drop constraint if exists import_transaction_registry_pkey;

alter table public.import_transaction_registry
  add constraint import_transaction_registry_pkey
  primary key (workspace_id, transaction_fingerprint);

drop index if exists public.transactions_import_transaction_fingerprint_unique;

do $$
begin
  if exists (
    select 1
    from public.transactions
    where import_transaction_fingerprint is not null
    group by workspace_id, import_transaction_fingerprint
    having count(*) > 1
  ) then
    raise exception
      'Migration 019 blocked: duplicate import fingerprints exist within a workspace';
  end if;
end $$;

create unique index transactions_workspace_import_fingerprint_unique
  on public.transactions (workspace_id, import_transaction_fingerprint)
  where import_transaction_fingerprint is not null;

drop index if exists public.transactions_canonical_fingerprint_unique;

do $$
begin
  if exists (
    select 1
    from public.transactions
    where canonical_fingerprint is not null
    group by workspace_id, canonical_fingerprint
    having count(*) > 1
  ) then
    raise exception
      'Migration 019 blocked: duplicate canonical fingerprints exist within a workspace';
  end if;
end $$;

create unique index transactions_workspace_canonical_fingerprint_unique
  on public.transactions (workspace_id, canonical_fingerprint)
  where canonical_fingerprint is not null;

drop index if exists public.import_transaction_registry_status_idx;

create index import_transaction_registry_workspace_status_idx
  on public.import_transaction_registry (workspace_id, status);
