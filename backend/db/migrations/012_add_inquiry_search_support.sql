-- Week 1 Omon Inquiry Engine search foundation.
-- Adds a normalized text field and indexes for low-resource keyword inquiry.

create extension if not exists pg_trgm;

alter table transactions
  add column if not exists search_text_normalized text not null default '';

update transactions
set search_text_normalized = trim(
  regexp_replace(
    lower(
      concat_ws(
        ' ',
        title,
        raw_category,
        raw_payload->>'_category_normalized',
        source_fund,
        note
      )
    ),
    '\s+',
    ' ',
    'g'
  )
)
where search_text_normalized = '';

create index if not exists transactions_search_text_normalized_trgm_idx
  on transactions using gin (search_text_normalized gin_trgm_ops);

create index if not exists transactions_workspace_transaction_date_desc_idx
  on transactions (workspace_id, transaction_date desc, created_at desc);
