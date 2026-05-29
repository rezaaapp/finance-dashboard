-- Initial PostgreSQL schema for the multi-tenant finance dashboard.
-- Recommended for Supabase/Neon: run this in a migration, not ad hoc from app code.

create extension if not exists pgcrypto;
create extension if not exists citext;

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email citext not null unique,
  name text not null,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  subscription_status text not null default 'free',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint workspaces_subscription_status_check
    check (subscription_status in ('free', 'premium'))
);

create table if not exists workspace_members (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null,
  user_id uuid not null,
  role text not null default 'member',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint workspace_members_workspace_id_fkey
    foreign key (workspace_id)
    references workspaces (id)
    on delete cascade,

  constraint workspace_members_user_id_fkey
    foreign key (user_id)
    references users (id)
    on delete cascade,

  constraint workspace_members_role_check
    check (role in ('owner', 'member')),

  constraint workspace_members_workspace_user_unique
    unique (workspace_id, user_id)
);

create table if not exists workspace_configurations (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null unique,
  google_sheet_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint workspace_configurations_workspace_id_fkey
    foreign key (workspace_id)
    references workspaces (id)
    on delete cascade
);

create table if not exists user_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique,
  access_token text not null,
  refresh_token text not null,
  token_expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint user_tokens_user_id_fkey
    foreign key (user_id)
    references users (id)
    on delete cascade
);

create index if not exists workspace_members_user_id_idx
  on workspace_members (user_id);

create index if not exists workspace_members_workspace_id_idx
  on workspace_members (workspace_id);

create index if not exists user_tokens_token_expires_at_idx
  on user_tokens (token_expires_at);

drop trigger if exists set_users_updated_at on users;
create trigger set_users_updated_at
before update on users
for each row
execute function set_updated_at();

drop trigger if exists set_workspaces_updated_at on workspaces;
create trigger set_workspaces_updated_at
before update on workspaces
for each row
execute function set_updated_at();

drop trigger if exists set_workspace_members_updated_at on workspace_members;
create trigger set_workspace_members_updated_at
before update on workspace_members
for each row
execute function set_updated_at();

drop trigger if exists set_workspace_configurations_updated_at on workspace_configurations;
create trigger set_workspace_configurations_updated_at
before update on workspace_configurations
for each row
execute function set_updated_at();

drop trigger if exists set_user_tokens_updated_at on user_tokens;
create trigger set_user_tokens_updated_at
before update on user_tokens
for each row
execute function set_updated_at();
