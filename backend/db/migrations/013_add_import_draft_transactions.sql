-- Incremental import draft persistence.
-- This stores parsed import drafts and duplicate markers only.

create table if not exists public.import_draft_transactions (
  id uuid primary key default gen_random_uuid(),
  import_job_id uuid not null references public.import_jobs(id) on delete cascade,
  transaction_fingerprint text not null,
  datetime text not null,
  merchant_original text not null,
  merchant_normalized text not null,
  amount numeric(18, 2) not null,
  direction text not null,
  transaction_type text not null,
  review_group text not null default '',
  raw_text text not null,
  is_existing boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists import_draft_transactions_import_job_id_idx
  on public.import_draft_transactions (import_job_id);

create index if not exists import_draft_transactions_fingerprint_idx
  on public.import_draft_transactions (transaction_fingerprint);

create index if not exists import_draft_transactions_is_existing_idx
  on public.import_draft_transactions (is_existing);
