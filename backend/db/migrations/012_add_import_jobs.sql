-- Smart Import foundation.
-- This stores generic upload jobs only; parsed transaction persistence is future scope.

create table if not exists public.import_jobs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  provider text not null default 'unknown',
  filename text not null,
  status text not null default 'uploaded',
  created_at timestamptz not null default now(),
  completed_at timestamptz null,

  constraint import_jobs_status_check
    check (status in (
      'uploaded',
      'parsing',
      'review',
      'approved',
      'completed',
      'failed',
      'expired'
    ))
);

create index if not exists import_jobs_workspace_id_idx
  on public.import_jobs (workspace_id);

create index if not exists import_jobs_status_idx
  on public.import_jobs (status);

create index if not exists import_jobs_created_at_idx
  on public.import_jobs (created_at);
