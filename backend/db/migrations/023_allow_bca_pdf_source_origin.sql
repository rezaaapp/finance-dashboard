-- Multi-provider Smart Import foundation.
-- BCA remains disabled at the application boundary until its parser is available.

alter table public.transactions
  drop constraint if exists transactions_source_origin_check;

alter table public.transactions
  add constraint transactions_source_origin_check
  check (source_origin in ('google_sheet', 'blu_pdf', 'bca_pdf'));
