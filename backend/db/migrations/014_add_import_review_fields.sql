-- Review lifecycle fields for import jobs and draft transactions.

alter table public.import_jobs
  add column if not exists transactions_found integer not null default 0,
  add column if not exists new_transactions integer not null default 0,
  add column if not exists existing_transactions integer not null default 0;

alter table public.import_draft_transactions
  add column if not exists status text not null default 'new',
  add column if not exists category text not null default '',
  add column if not exists notes text not null default '',
  add column if not exists updated_at timestamptz not null default now();

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'import_draft_transactions_status_check'
  ) then
    alter table public.import_draft_transactions
      add constraint import_draft_transactions_status_check
      check (status in ('new', 'approved'));
  end if;
end $$;

create index if not exists import_draft_transactions_status_idx
  on public.import_draft_transactions (status);

create index if not exists import_draft_transactions_review_group_idx
  on public.import_draft_transactions (review_group);

drop trigger if exists set_import_draft_transactions_updated_at on public.import_draft_transactions;
create trigger set_import_draft_transactions_updated_at
before update on public.import_draft_transactions
for each row
execute function set_updated_at();
