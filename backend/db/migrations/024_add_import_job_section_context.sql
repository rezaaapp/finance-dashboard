-- Persist safe provider-specific import context for review and history.
-- Existing jobs and Blu imports retain an empty JSON object.

alter table public.import_jobs
  add column if not exists section_context jsonb not null default '{}'::jsonb;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'import_jobs_section_context_object_check'
      and conrelid = 'public.import_jobs'::regclass
  ) then
    alter table public.import_jobs
      add constraint import_jobs_section_context_object_check
      check (jsonb_typeof(section_context) = 'object');
  end if;
end $$;
