# Rule-Based Classification

Week 5 MVP uses deterministic rule-based classification only. AI providers,
external APIs, and local LLMs are disabled by default.

Default AI-related environment settings:

```env
AI_CLASSIFICATION_ENABLED=false
AI_PROVIDER=rule_based
AI_MODEL=none
```

End-to-end SQL, endpoint, and UI verification steps are documented in
`docs/WEEK5_RULE_BASED_VERIFICATION.md`.

## Output Fields

- `direction`: `income`, `expense`, or `saving_transfer`
- `financial_type`: `income`, `need`, `want`, `saving`, or `uncategorized`
- `category`: normalized transaction category
- `confidence_score`: rule confidence from `0.40` to `0.95`
- `method`: `rule`
- `explanation`: short safe reason for the matched rule

## Rule Priority

1. Manual override (`method = 'manual'` or `status = 'manual_override'`)
2. User-defined workspace rules
3. Built-in explicit expense rules
4. Built-in income rules
5. Built-in saving rules
6. Built-in need rules
7. Built-in want rules
8. Existing direction fallback
9. Uncategorized fallback

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

Uncategorized is an official bucket, not an error state. It should stay visible
in Need/Want/Saving/Income/Uncategorized charts so users can see classification
coverage.

## Insight Threshold Settings

Workspace severity thresholds are available through:

- `GET /api/settings/insight-thresholds`
- `PUT /api/settings/insight-thresholds`

The API stores workspace-specific thresholds in `workspace_insight_settings`.
If a workspace has no saved settings yet, the API returns config defaults with
`source = "default"`. Once saved, it returns `source = "workspace"`.

Environment variables such as `INSIGHT_NEED_WARNING_RATIO`,
`INSIGHT_WANT_DANGER_RATIO`, and `INSIGHT_ANOMALY_WARNING_MULTIPLIER` are only
fallback defaults. They are not required for the app to start, and database
workspace settings take priority.

## Rule-Based Insights

`GET /api/dashboard/rule-based-insights?year=2026&month=5` returns lightweight
template insights using aggregated data only. Metrics include need ratio, want
ratio, saving rate, uncategorized count, total expense, income, saving, and top
financial type.

The insight engine is rule-based only. It does not use an AI provider, external
API, local LLM, or extra dependency. Empty periods return
`Not enough data to generate insights yet.` without inventing trends.

Highlights are structured JSON objects, not HTML or markdown. Each highlight
includes `type`, `label`, `severity`, `message`, `amount`, and either `ratio` or
`count` when relevant. Severity values are `positive`, `neutral`, `info`,
`warning`, and `danger`.

The backend determines severity from effective workspace thresholds. Frontend
surfaces should render the returned severity and should not recalculate it.
Need and Want severity use expense ratios, Saving severity uses saving rate
against income, and Uncategorized severity uses uncategorized transaction count.

## Dashboard And Configuration UI

The Dashboard renders backend-driven rule-based insights in the Financial
Insights section. Cards show the backend-provided `severity` badge for Need,
Want, Saving, Income, Uncategorized, and Top Category when available. The
frontend renders severity but does not calculate severity thresholds.

The Dashboard also includes Financial Type Breakdown and Monthly Financial Type
Trend charts for Need, Want, Saving, Income, and Uncategorized.

Configuration includes Insight Severity Settings:

- Need, Want, and Saving thresholds use sliders plus numeric percentage inputs.
- Uncategorized severity uses count inputs.
- Anomaly severity uses multiplier inputs.
- Reset to Defaults fills the form defaults; users still click Save Settings to
  persist them because there is no dedicated backend reset endpoint.

## Anomaly Explanation

`GET /api/dashboard/anomalies?year=2026&month=5` excludes Income and Saving,
then checks expense-like transactions (`need`, `want`, and `uncategorized`) by
category. A transaction is flagged when it is above category average plus two
standard deviations, or when low-variance data is more than 2x the category
average. Each anomaly includes a short explanation and does not expose raw
payloads. Anomaly severity uses workspace thresholds:
`anomaly_warning_multiplier` and `anomaly_danger_multiplier`.

## Known Limitations

Classification run default mode processes unclassified transactions only.
Manual overrides are never overwritten. When a suggested rule is applied with
`apply_to_existing = true`, existing matching classifications can be refreshed
for non-manual rows, prioritizing Uncategorized and low-confidence
classifications.

AI adapters/providers are not implemented in Week 5. Full historical
reclassification is performed through bounded batch backfill or suggestion apply
flows, not through an always-on heavy process.
