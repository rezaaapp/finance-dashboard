-- Backfill the Inquiry Engine search index for Blu PDF transactions that were
-- approved before the import persistence path populated search_text_normalized.

update transactions
set search_text_normalized = trim(
  regexp_replace(
    lower(
      concat_ws(
        ' ',
        title,
        raw_category,
        raw_payload->>'_category_normalized',
        source_fund,
        note
      )
    ),
    '\s+',
    ' ',
    'g'
  )
)
where source_origin = 'blu_pdf'
  and search_text_normalized = '';
