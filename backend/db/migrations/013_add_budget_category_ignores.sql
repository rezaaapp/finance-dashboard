-- Per-period ignored unbudgeted categories for Budgeting & Alerts.

create table if not exists budget_category_ignores (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null
    references workspaces (id)
    on delete cascade,
  year integer not null,
  month integer not null,
  category text not null,
  created_at timestamptz not null default now(),

  constraint budget_category_ignores_period_check
    check (
      year >= 2000
      and year <= 2100
      and month >= 1
      and month <= 12
    ),

  constraint budget_category_ignores_category_not_blank_check
    check (length(trim(category)) > 0),

  constraint budget_category_ignores_workspace_period_category_unique
    unique (workspace_id, year, month, category)
);

create index if not exists budget_category_ignores_workspace_period_idx
  on budget_category_ignores (workspace_id, year, month);
