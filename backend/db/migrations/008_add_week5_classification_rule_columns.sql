-- Week 5 user-defined rule columns.
-- Existing allocation_type rules remain intact for backward compatibility.

alter table if exists classification_rules
add column if not exists direction text,
add column if not exists financial_type text,
add column if not exists category text,
add column if not exists confidence_score numeric(5, 4),
add column if not exists explanation text;

create index if not exists classification_rules_financial_type_idx
  on classification_rules (financial_type);

create index if not exists classification_rules_priority_idx
  on classification_rules (priority);
