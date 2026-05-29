alter table workspace_configurations
add column if not exists google_sheet_sources jsonb not null default '[]'::jsonb;

update workspace_configurations
set google_sheet_sources = jsonb_build_array(
  jsonb_build_object(
    'id', google_sheet_id,
    'label', 'Source 1',
    'status', 'active'
  )
)
where google_sheet_id is not null
  and google_sheet_id <> ''
  and google_sheet_sources = '[]'::jsonb;
