-- Ensure Google OAuth upsert can target one active connection per workspace user.

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'google_oauth_connections_workspace_user_unique'
      and conrelid = 'google_oauth_connections'::regclass
  ) then
    alter table google_oauth_connections
      add constraint google_oauth_connections_workspace_user_unique
      unique (workspace_id, user_id);
  end if;
end $$;
