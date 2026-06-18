alter table public.import_jobs
  add column if not exists statement_owner text;

alter table public.import_draft_transactions
  add column if not exists statement_owner text,
  add column if not exists source_fund text not null default 'Blu',
  add column if not exists canonical_fingerprint text,
  add column if not exists canonical_fingerprint_date text;

alter table public.transactions
  add column if not exists source_origin text,
  add column if not exists source_reference text,
  add column if not exists canonical_fingerprint text,
  add column if not exists canonical_fingerprint_date text;

update public.import_jobs
set statement_owner = nullif(btrim(statement_owner), '');

update public.import_jobs jobs
set statement_owner = normalized_owner.statement_owner
from (
  select
    t.import_job_id,
    min(nullif(btrim(t.user_name), '')) as statement_owner
  from public.transactions t
  where t.import_job_id is not null
    and nullif(btrim(t.user_name), '') is not null
  group by t.import_job_id
) normalized_owner
where jobs.id = normalized_owner.import_job_id
  and nullif(btrim(jobs.statement_owner), '') is null;

update public.import_draft_transactions drafts
set statement_owner = jobs.statement_owner
from public.import_jobs jobs
where drafts.import_job_id = jobs.id
  and nullif(btrim(drafts.statement_owner), '') is null
  and nullif(btrim(jobs.statement_owner), '') is not null;

update public.transactions
set user_name = nullif(btrim(user_name), '');

update public.transactions
set user_name = nullif(btrim(raw_payload->>'Nama'), '')
where nullif(btrim(user_name), '') is null
  and nullif(btrim(raw_payload->>'Nama'), '') is not null;

update public.transactions transactions
set user_name = jobs.statement_owner
from public.import_jobs jobs
where transactions.import_job_id = jobs.id
  and nullif(btrim(transactions.user_name), '') is null
  and nullif(btrim(jobs.statement_owner), '') is not null;

update public.transactions
set source_origin = case
  when import_job_id is not null or import_transaction_fingerprint is not null then 'blu_pdf'
  else 'google_sheet'
end
where source_origin is null;

update public.transactions
set source_reference = case
  when source_origin = 'blu_pdf' and import_job_id is not null and import_transaction_fingerprint is not null then
    concat('import_job:', import_job_id::text, '|fingerprint:', import_transaction_fingerprint)
  when source_origin = 'google_sheet' and sheet_source_id is not null and external_row_key is not null then
    concat('sheet_source:', sheet_source_id::text, '|row:', external_row_key)
  else source_reference
end
where source_reference is null;

update public.transactions
set canonical_fingerprint = encode(
  digest(
    concat_ws(
      '|',
      lower(coalesce(nullif(btrim(user_name), ''), nullif(btrim(raw_payload->>'Nama'), ''), '')),
      case
        when transaction_time is not null then to_char(transaction_time, 'YYYY-MM-DD"T"HH24:MI')
        when transaction_date is not null then to_char(transaction_date, 'YYYY-MM-DD')
        else ''
      end,
      lower(regexp_replace(coalesce(nullif(btrim(title), ''), ''), '\s+', ' ', 'g')),
      trim(to_char(amount, 'FM999999999999999990D00')),
      lower(coalesce(nullif(btrim(direction), ''), '')),
      lower(coalesce(nullif(btrim(source_fund), ''), ''))
    ),
    'sha256'
  ),
  'hex'
)
where canonical_fingerprint is null
  and transaction_date is not null;

update public.transactions
set canonical_fingerprint_date = encode(
  digest(
    concat_ws(
      '|',
      lower(coalesce(nullif(btrim(user_name), ''), nullif(btrim(raw_payload->>'Nama'), ''), '')),
      coalesce(to_char(transaction_date, 'YYYY-MM-DD'), ''),
      lower(regexp_replace(coalesce(nullif(btrim(title), ''), ''), '\s+', ' ', 'g')),
      trim(to_char(amount, 'FM999999999999999990D00')),
      lower(coalesce(nullif(btrim(direction), ''), '')),
      lower(coalesce(nullif(btrim(source_fund), ''), ''))
    ),
    'sha256'
  ),
  'hex'
)
where canonical_fingerprint_date is null
  and transaction_date is not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'transactions_source_origin_check'
  ) then
    alter table public.transactions
      add constraint transactions_source_origin_check
      check (source_origin in ('google_sheet', 'blu_pdf'));
  end if;
end $$;

create index if not exists import_jobs_statement_owner_idx
  on public.import_jobs (statement_owner);

create index if not exists import_draft_transactions_statement_owner_idx
  on public.import_draft_transactions (statement_owner);

create index if not exists import_draft_transactions_canonical_fingerprint_idx
  on public.import_draft_transactions (canonical_fingerprint);

create index if not exists transactions_source_origin_idx
  on public.transactions (source_origin);

create index if not exists transactions_source_reference_idx
  on public.transactions (source_reference);

create index if not exists transactions_canonical_fingerprint_idx
  on public.transactions (canonical_fingerprint);

create index if not exists transactions_canonical_fingerprint_date_idx
  on public.transactions (canonical_fingerprint_date);

do $$
begin
  if not exists (
    select 1
    from pg_indexes
    where schemaname = 'public'
      and indexname = 'transactions_canonical_fingerprint_unique'
  ) and not exists (
    select 1
    from public.transactions
    where canonical_fingerprint is not null
    group by canonical_fingerprint
    having count(*) > 1
  ) then
    create unique index transactions_canonical_fingerprint_unique
      on public.transactions (canonical_fingerprint)
      where canonical_fingerprint is not null;
  end if;
end $$;
