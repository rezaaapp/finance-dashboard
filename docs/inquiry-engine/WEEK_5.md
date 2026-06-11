# Week 5 Smart Summary Engine

## Scope

Week 5 adds deterministic Smart Insight output to `POST /api/inquiry`. The goal is to make inquiry results feel more useful without AI, embeddings, Redis, or external search services.

The result order is now:

```text
Ringkasan -> Summary Cards -> Smart Insight -> Preview -> Evidence Layer
```

## Response Field

`POST /api/inquiry` now includes:

```json
{
  "insights": [
    {
      "type": "largest_transaction",
      "title": "Transaksi terbesar",
      "message": "Transaksi terbesar untuk pencarian ini adalah Rp250.000 dari Kopi Kenangan.",
      "value": 250000
    }
  ]
}
```

No-result responses return `insights: []`.

## Metrics Implemented

- `total_transactions`
- `total_amount`
- `average_amount`
- `min_amount`
- `max_amount`
- `first_transaction_date`
- `last_transaction_date`
- `top_category`
- `top_source_fund`
- `largest_transaction`

## Metrics Skipped

Trend comparison against the previous equivalent period is deferred. It needs additional period-boundary handling and extra queries, so Week 5 keeps the implementation focused on low-resource current-context aggregates.

## Performance Strategy

- Insights are generated from SQL aggregates and `LIMIT 1` queries.
- Matching transactions are not loaded into Python.
- Runtime search still uses `search_text_normalized`.
- No `LOWER(column)` is used in runtime search `WHERE`.
- Queries remain workspace scoped and context scoped.
- Preview remains max 10.
- Detail remains lazy fetched and paginated with `limit=25`.

## UI Behavior

The Search page renders `Smart Insight` only when `insights` is non-empty. Final visual polishing and proportional sizing remain deferred.

## Constraints Confirmed

- No AI or LLM used.
- No embeddings used.
- No Redis used.
- No Elasticsearch, OpenSearch, or Meilisearch used.
- No global header search added.
