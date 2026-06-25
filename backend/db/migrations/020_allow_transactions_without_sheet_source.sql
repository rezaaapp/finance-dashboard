-- Blu PDF approvals persist to the Omon ledger even when no Google Sheet
-- projection target is configured.

alter table public.transactions
  alter column sheet_source_id drop not null;
