-- Workspace monthly category budgets for Budgeting & Alerts.

create table if not exists budgets (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null
    references workspaces (id)
    on delete cascade,
  year integer not null,
  month integer not null,
  category text not null,
  amount numeric(18, 2) not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint budgets_period_check
    check (
      year >= 2000
      and year <= 2100
      and month >= 1
      and month <= 12
    ),

  constraint budgets_amount_non_negative_check
    check (amount >= 0),

  constraint budgets_category_not_blank_check
    check (length(trim(category)) > 0),

  constraint budgets_workspace_period_category_unique
    unique (workspace_id, year, month, category)
);

create index if not exists budgets_workspace_period_idx
  on budgets (workspace_id, year, month);

drop trigger if exists set_budgets_updated_at on budgets;
create trigger set_budgets_updated_at
before update on budgets
for each row
execute function set_updated_at();
