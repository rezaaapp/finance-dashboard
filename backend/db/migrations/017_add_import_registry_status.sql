-- Remember both approved and rejected Smart Import fingerprints.

alter table public.import_transaction_registry
  add column if not exists status text,
  add column if not exists rejected_at timestamptz,
  add column if not exists last_seen_at timestamptz;

alter table public.import_transaction_registry
  alter column approved_at drop not null;

update public.import_transaction_registry
set
  status = coalesce(status, 'approved'),
  last_seen_at = coalesce(last_seen_at, approved_at, created_at)
where status is null
   or last_seen_at is null;

alter table public.import_transaction_registry
  alter column status set default 'approved',
  alter column status set not null,
  alter column last_seen_at set default now(),
  alter column last_seen_at set not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'import_transaction_registry_status_check'
  ) then
    alter table public.import_transaction_registry
      add constraint import_transaction_registry_status_check
      check (status in ('approved', 'rejected'));
  end if;
end $$;

create index if not exists import_transaction_registry_status_idx
  on public.import_transaction_registry (status);
