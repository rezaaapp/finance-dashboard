-- Final transaction persistence metadata and incremental fingerprint registry.

create table if not exists public.import_transaction_registry (
  transaction_fingerprint text primary key,
  provider text not null,
  created_at timestamptz not null default now(),
  approved_at timestamptz not null default now()
);

alter table public.transactions
  add column if not exists user_name text,
  add column if not exists import_job_id uuid references public.import_jobs(id) on delete set null,
  add column if not exists import_transaction_fingerprint text,
  add column if not exists sync_status text not null default 'pending',
  add column if not exists sync_error_message text;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'transactions_sync_status_check'
  ) then
    alter table public.transactions
      add constraint transactions_sync_status_check
      check (sync_status in ('pending', 'success', 'failed', 'needs_reconnect'));
  end if;
end $$;

create unique index if not exists transactions_import_transaction_fingerprint_unique
  on public.transactions (import_transaction_fingerprint)
  where import_transaction_fingerprint is not null;

create index if not exists transactions_import_job_id_idx
  on public.transactions (import_job_id);

create index if not exists transactions_sync_status_idx
  on public.transactions (sync_status);
