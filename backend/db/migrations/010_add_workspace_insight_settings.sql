-- Workspace-level rule-based insight threshold settings.

create table if not exists workspace_insight_settings (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null
    references workspaces (id)
    on delete cascade,
  need_warning_ratio numeric(6, 4) not null default 0.80,
  need_danger_ratio numeric(6, 4) not null default 0.90,
  want_warning_ratio numeric(6, 4) not null default 0.30,
  want_danger_ratio numeric(6, 4) not null default 0.45,
  saving_warning_ratio numeric(6, 4) not null default 0.10,
  saving_good_ratio numeric(6, 4) not null default 0.20,
  uncategorized_warning_count integer not null default 1,
  uncategorized_danger_count integer not null default 20,
  anomaly_warning_multiplier numeric(6, 2) not null default 2.0,
  anomaly_danger_multiplier numeric(6, 2) not null default 3.0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint workspace_insight_settings_workspace_unique
    unique (workspace_id),

  constraint workspace_insight_settings_ratio_range_check
    check (
      need_warning_ratio >= 0 and need_warning_ratio <= 1
      and need_danger_ratio >= 0 and need_danger_ratio <= 1
      and want_warning_ratio >= 0 and want_warning_ratio <= 1
      and want_danger_ratio >= 0 and want_danger_ratio <= 1
      and saving_warning_ratio >= 0 and saving_warning_ratio <= 1
      and saving_good_ratio >= 0 and saving_good_ratio <= 1
    ),

  constraint workspace_insight_settings_ratio_order_check
    check (
      need_warning_ratio <= need_danger_ratio
      and want_warning_ratio <= want_danger_ratio
      and saving_warning_ratio <= saving_good_ratio
    ),

  constraint workspace_insight_settings_count_check
    check (
      uncategorized_warning_count >= 0
      and uncategorized_danger_count >= 0
      and uncategorized_warning_count <= uncategorized_danger_count
    ),

  constraint workspace_insight_settings_anomaly_check
    check (
      anomaly_warning_multiplier > 0
      and anomaly_danger_multiplier > 0
      and anomaly_warning_multiplier <= anomaly_danger_multiplier
    )
);

create index if not exists workspace_insight_settings_workspace_id_idx
  on workspace_insight_settings (workspace_id);

drop trigger if exists set_workspace_insight_settings_updated_at
  on workspace_insight_settings;
create trigger set_workspace_insight_settings_updated_at
before update on workspace_insight_settings
for each row
execute function set_updated_at();
