# Week 3 Evidence Layer

## Scope

Week 3 adds an inline Evidence Layer below the existing inquiry result flow. Search still presents the answer first, then summary cards, then the max-10 preview before any detail rows are shown.

## Result Flow

```text
Ringkasan -> Summary -> Preview (10) -> Expandable Evidence Layer -> Pagination
```

No popup, modal, navigation, or separate detail page is used.

## Lazy Fetch

Detail rows are not requested during the initial inquiry request. The frontend calls `GET /api/inquiry/detail` only after the user expands `Lihat Detail`.

The initial inquiry still uses `POST /api/inquiry` and returns only answer, summary, preview, and `detail_available`.

## Client Cache

Detail pages are cached in React state by `offset`.

- Closing and reopening the detail layer reuses cached data.
- Submitting a new inquiry clears the detail cache, rows, page, and offset.
- Pagination requests only the selected page.

## Pagination

The detail request uses:

```text
limit=25
offset=page_offset
```

The backend caps detail `limit` at 25. Previous is disabled on page 1. Next is disabled when the API returns `has_more: false`.

## Detail Response

Preferred response fields:

```json
{
  "query": "kopi",
  "items": [],
  "limit": 25,
  "offset": 0,
  "count": 25,
  "has_more": true
}
```

The response also keeps `transactions` and `total_transactions` for compatibility with earlier Week 1/2 code.

## Performance Strategy

- Detail is fetched only after explicit expansion.
- Duplicate detail requests are blocked while loading.
- Reopening the detail layer uses cached state.
- Pagination fetches only one page at a time.
- The summary and preview remain visible while detail loads.
- No AI, Redis, or external search service is introduced.
