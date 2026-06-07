-- Week 6F workspace invitation lifecycle.
-- Pending invitations are stored separately from active workspace_members.

create table if not exists public.workspace_invitations (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  email text not null,
  role text not null default 'member',
  status text not null default 'pending',
  invited_by_user_id uuid not null references public.users(id),
  invited_user_id uuid null references public.users(id),
  token text null,
  expires_at timestamptz null,
  responded_at timestamptz null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint workspace_invitations_role_check
    check (role in ('member')),

  constraint workspace_invitations_status_check
    check (status in ('pending', 'accepted', 'declined', 'expired', 'cancelled'))
);

create unique index if not exists workspace_invitations_pending_email_unique
  on public.workspace_invitations (workspace_id, lower(email))
  where status = 'pending';

create index if not exists workspace_invitations_workspace_id_idx
  on public.workspace_invitations (workspace_id);

create index if not exists workspace_invitations_lower_email_idx
  on public.workspace_invitations (lower(email));

create index if not exists workspace_invitations_status_idx
  on public.workspace_invitations (status);

create index if not exists workspace_invitations_invited_user_id_idx
  on public.workspace_invitations (invited_user_id);

create index if not exists workspace_invitations_created_at_idx
  on public.workspace_invitations (created_at);

drop trigger if exists set_workspace_invitations_updated_at on public.workspace_invitations;
create trigger set_workspace_invitations_updated_at
before update on public.workspace_invitations
for each row
execute function set_updated_at();
