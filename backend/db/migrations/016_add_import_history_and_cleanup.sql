-- Import history, retry sync, and cleanup lifecycle metadata.

alter table public.import_jobs
  add column if not exists rejected_transactions integer not null default 0,
  add column if not exists temp_file_path text,
  add column if not exists temp_file_deleted_at timestamptz,
  add column if not exists expires_at timestamptz,
  add column if not exists cleanup_completed_at timestamptz;

do $$
begin
  if exists (
    select 1
    from pg_constraint
    where conname = 'import_jobs_status_check'
  ) then
    alter table public.import_jobs
      drop constraint import_jobs_status_check;
  end if;

  alter table public.import_jobs
    add constraint import_jobs_status_check
    check (status in (
      'uploaded',
      'parsing',
      'review',
      'approved',
      'completed',
      'failed',
      'expired',
      'cleanup_completed'
    ));
end $$;

create index if not exists import_jobs_expires_at_idx
  on public.import_jobs (expires_at);

create index if not exists import_jobs_temp_file_deleted_at_idx
  on public.import_jobs (temp_file_deleted_at);
