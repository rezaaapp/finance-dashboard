# Rule-Based Classification

Week 5 MVP uses deterministic rule-based classification only. AI providers,
external APIs, and local LLMs are disabled by default.

## Output Fields

- `direction`: `income`, `expense`, or `saving_transfer`
- `financial_type`: `income`, `need`, `want`, `saving`, or `uncategorized`
- `category`: normalized transaction category
- `confidence_score`: rule confidence from `0.40` to `0.95`
- `method`: `rule`
- `explanation`: short safe reason for the matched rule

## Rule Priority

1. Explicit expense rules
2. Income rules
3. Saving rules
4. Need rules
5. Want rules
6. Existing direction fallback
7. Uncategorized fallback

Fields are checked case-insensitively in this order: `raw_category`, `title`,
`source_fund`, `note`, then `raw_payload._sheet_name`.

## Keyword Examples

- Income: `income`, `gaji`, `salary`, `bonus`
- Saving: `saving`, `tabungan`, `investasi`, `reksadana`
- Need: `groceries`, `tagihan`, `listrik`, `kesehatan`
- Want: `jajan`, `gift`, `shopping`, `travel`

Manual override priority is supported by the repository: rows with
`method = 'manual'` are not overwritten. AI adapter support is planned for a
later prompt and remains disabled by default.

## API Endpoints

- `POST /api/classifications/run?limit=100`: run bounded rule-based
  classification for unclassified transactions only. The endpoint also accepts
  `{"limit": 100}` in the request body. The limit is clamped between `1` and
  `AI_MAX_TRANSACTIONS_PER_RUN`, with a hard cap of `500`.
- `GET /api/classifications/summary`: return classified, unclassified,
  low-confidence, manual, rule, and AI counters.
- `GET /api/classifications/low-confidence`: list current classifications below
  a confidence threshold.
- `PUT /api/classifications/transactions/{transaction_id}/manual`: save a manual
  correction with `method = 'manual'` and `status = 'manual_override'`.
- `GET /api/classifications/rules`: list workspace user-defined rules.
- `POST /api/classifications/rules`: create a user-defined rule.
- `PUT /api/classifications/rules/{rule_id}`: update a user-defined rule.
- `DELETE /api/classifications/rules/{rule_id}`: delete a user-defined rule.
- `GET /api/classifications/uncategorized/groups`: group Uncategorized
  transactions by raw category, title keyword, or source fund.
- `GET /api/classifications/suggestions`: propose deterministic bulk rules for
  Uncategorized groups.
- `POST /api/classifications/suggestions/apply`: create or update a
  user-defined rule and optionally apply it to existing non-manual matches.

User-defined rules are workspace scoped and evaluated before built-in keyword
rules. They support `exact`, `contains`, and `regex` match types, with bounded
batch execution and no external calls.

Bulk suggestions are rule-based only. High-confidence examples include income,
saving, bills, gift, subscriptions, household, food, and transport keywords.
Ambiguous marketplace or bank-like patterns such as Tokopedia, Shopee,
transfer, BCA, and Mandiri are not suggested unless future prompts add stronger
supporting context. Applying a suggestion never overwrites `method = 'manual'`
or `status = 'manual_override'`.

Batch responses include `duration_ms`. Backend logs record safe timing counters
for run start, unclassified load, rules load, in-memory classification, bulk
upsert, and run finish without logging transaction titles, notes, raw payloads,
tokens, or secrets.

## Sync Integration

`POST /api/data-sources/{source_id}/sync` automatically runs rule-based
classification for transactions inserted or updated by the Google Sheet sync.
User-defined rules are loaded once per sync classification run and are evaluated
before built-in rules. Manual overrides are never overwritten.

The sync response includes a `classification` summary with `processed`,
`classified`, `updated`, `low_confidence`, `skipped_manual`, `errors`, and
`duration_ms`. If sync succeeds but classification fails, the response may
include `warnings: ["classification_failed"]`; users can still run
`POST /api/classifications/run` later for backfill.

## Financial Type Analytics

Dashboard analytics can read current classifications for Need, Want, Saving,
Income, and Uncategorized views:

- `GET /api/dashboard/financial-types?year=2026&month=5`
- `GET /api/dashboard/monthly-financial-types?year=2026`

If a transaction has not been classified yet, analytics safely falls back from
`transactions.direction`: `income` maps to Income, `saving_transfer` maps to
Saving, and `expense` maps to Uncategorized. Queries are workspace scoped and
only count actual transactions with `transaction_date <= current_date`.

## Rule-Based Insights

`GET /api/dashboard/rule-based-insights?year=2026&month=5` returns lightweight
template insights using aggregated data only. Metrics include need ratio, want
ratio, saving rate, total expense, income, saving, and top financial type.

The insight engine is rule-based only. It does not use an AI provider, external
API, local LLM, or extra dependency. Empty periods return
`Not enough data to generate insights yet.` without inventing trends.

## Anomaly Explanation

`GET /api/dashboard/anomalies?year=2026&month=5` excludes Income and Saving,
then checks expense-like transactions (`need`, `want`, and `uncategorized`) by
category. A transaction is flagged when it is above category average plus two
standard deviations, or when low-variance data is more than 2x the category
average. Each anomaly includes a short explanation and does not expose raw
payloads.

## Known Limitations

Classification run default mode processes unclassified transactions only.
Manual overrides are never overwritten. If a new user-defined rule is added,
existing `method = 'rule'` rows are not automatically reclassified yet.
Reclassification mode can be added in a later prompt.
