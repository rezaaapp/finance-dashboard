-- Week 5 classification batch performance indexes.
-- These are additive and safe for existing data.

create index if not exists transaction_classifications_workspace_transaction_current_idx
  on transaction_classifications (workspace_id, transaction_id, is_current);

create index if not exists transactions_workspace_transaction_date_idx
  on transactions (workspace_id, transaction_date desc, created_at desc);
