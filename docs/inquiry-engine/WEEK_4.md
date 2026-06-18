# Week 4 Search Context Engine

## Scope

Week 4 adds Search-local context controls so users can search with the active year/month context instead of repeating dates in every query. The Search page remains a dedicated sidebar page and keeps the Answer First, Evidence Second flow.

## Default Context Source

The Search page receives the current Dashboard year and month selection from the existing Dashboard React state.

- `selectedYear` initializes the Search year context.
- `selectedMonth` initializes the Search month context.
- If no year is selected, Search falls back to the current calendar year.
- Available year options reuse the existing Dashboard `available-years` data.

## All Months Behavior

Month supports an `All Months` option. When selected, Search omits `month` from:

- `POST /api/inquiry`
- `GET /api/inquiry/detail`

The backend already treats month as optional when a year is present.

## Context Change Behavior

Changing Year or Month inside Search clears stale result state:

- current result
- detail open state
- detail loading/error
- detail page cache
- page and offset

The query text is kept, but the user submits again. This avoids silently showing results from an old context.

## Detail Context Consistency

The detail endpoint uses the same query, year, and month as the summary request. Detail remains lazy fetched only when users expand `Lihat Detail`.

## Recent Search

Successful inquiries are stored locally in `localStorage` under:

```text
finance-dashboard-recent-inquiries
```

Each entry stores:

- query
- year
- month
- timestamp

Only the 5 most recent unique query/context pairs are kept. Clicking a recent search restores the query and context, then submits the inquiry.

## Keyboard UX

Enter submits the Search form when the query is valid and no request is loading. The `/` key focuses the Search input only when the user is not already typing in an input, textarea, select, or editable element.

## Constraints Confirmed

- No AI added.
- No Redis added.
- No external search service added.
- No global header search added.
- Preview remains max 10.
- Detail remains lazy fetched and paginated with `limit=25`.
