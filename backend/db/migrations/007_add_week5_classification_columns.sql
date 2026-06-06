-- Week 5 rule-based classification columns.
-- This extends the existing table without dropping or rewriting user data.

alter table if exists transaction_classifications
add column if not exists direction text,
add column if not exists financial_type text,
add column if not exists category text,
add column if not exists confidence_score numeric(5, 4),
add column if not exists method text,
add column if not exists explanation text,
add column if not exists updated_at timestamptz not null default now();

create index if not exists transaction_classifications_method_idx
  on transaction_classifications (method);

create index if not exists transaction_classifications_financial_type_idx
  on transaction_classifications (financial_type);

do $$
begin
  if not exists (
    select 1
    from pg_indexes
    where schemaname = current_schema()
      and indexname = 'transaction_classifications_workspace_transaction_current_unique'
  )
  and not exists (
    select 1
    from transaction_classifications
    where is_current = true
    group by workspace_id, transaction_id
    having count(*) > 1
  ) then
    execute '
      create unique index transaction_classifications_workspace_transaction_current_unique
      on transaction_classifications (workspace_id, transaction_id)
      where is_current = true
    ';
  end if;
end $$;

drop trigger if exists set_transaction_classifications_updated_at
  on transaction_classifications;
create trigger set_transaction_classifications_updated_at
before update on transaction_classifications
for each row
execute function set_updated_at();
