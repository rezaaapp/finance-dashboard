-- Add a global role for MVP user management.
-- Workspace-level roles still control workspace ownership/membership.

alter table users
  add column if not exists role text not null default 'user';

alter table users
  drop constraint if exists users_role_check;

alter table users
  add constraint users_role_check
  check (role in ('super_admin', 'owner', 'member', 'user'));

create index if not exists users_role_idx
  on users (role);
