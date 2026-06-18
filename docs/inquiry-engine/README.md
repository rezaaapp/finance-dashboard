# Omon Inquiry Engine

## Core Principle

Answer First, Evidence Second.

The inquiry flow returns a direct answer and compact summary before showing transaction evidence. Week 1 intentionally uses keyword search only, with no AI integration.

## Week 1 Scope

- Add a normalized keyword search field to `transactions`.
- Populate normalized search text for existing rows through migration.
- Generate normalized search text during Google Sheet transaction sync.
- Add read-only inquiry endpoints.
- Add a dedicated Search page in the sidebar.
- Show the answer first, summary cards second, and preview transactions third.

## API Contract

### POST `/api/inquiry`

Request:

```json
{
  "query": "kopi",
  "year": 2026,
  "month": 6
}
```

Response:

```json
{
  "query": "kopi",
  "intent": "keyword_search",
  "answer": "Ditemukan 5 transaksi terkait \"kopi\".",
  "summary": {
    "total_transactions": 5,
    "total_amount": 150000,
    "average_amount": 30000
  },
  "preview": [
    {
      "id": "transaction-id",
      "transaction_date": "2026-06-10",
      "transaction_name": "Kopi Kenangan",
      "category": "Makanan",
      "amount": 35000,
      "source_dana": "GoPay"
    }
  ],
  "detail_available": false
}
```

### GET `/api/inquiry/detail`

Example:

```text
/api/inquiry/detail?query=kopi&year=2026&month=6&limit=25&offset=0
```

Response includes `query`, `intent`, `limit`, `offset`, `total_transactions`, and paginated `transactions`.

## Performance Rules

- Query is required.
- Query is trimmed in backend code.
- Minimum query length is 2 characters.
- Maximum query length is 100 characters.
- Preview is limited to 10 latest transactions.
- Detail results are paginated with `limit` and `offset`.
- `LOWER(column)` is not used in search `WHERE` clauses.
- Search uses `transactions.search_text_normalized`.
- New transaction sync writes normalized lowercase search text in application code.
- `pg_trgm` is enabled.
- `search_text_normalized` has a GIN trigram index.
- Workspace and transaction-date indexes support scoped latest-result lookups.
- Endpoints are read-only and do not load all matching rows.

## Future Roadmap

- Week 2: Answer First UI
- Week 3: Evidence Layer
- Week 4: Search UX
- Week 5: Smart Intent
- Week 6: AI-ready foundation
