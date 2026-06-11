# Week 2 Inquiry Result Experience

## Scope

Week 2 improves the dedicated Search page so it behaves like an answer-first inquiry interface rather than a transaction filter page. The backend architecture remains the Week 1 keyword inquiry foundation.

## Result Order

The result order remains:

```text
Ringkasan -> Summary Cards -> Preview Transactions -> Detail
```

The page must not show a full transaction table before the answer.

## UI State Behavior

- Empty: before any query, the page shows guidance and example chips for `kopi`, `groceries`, `indomaret`, and `transport`.
- Loading: while the inquiry request is running, the page shows "Omon sedang menyiapkan ringkasan..." plus skeleton placeholders for Ringkasan, summary cards, and preview.
- Success: the page shows Ringkasan first, then Transactions, Total Amount, and Average cards, then a max-10 latest transaction preview.
- No result: when `summary.total_transactions` is `0` or preview is empty, the page shows a friendly no-result message instead of an empty list.
- Error: API failures show a readable message without exposing backend stack traces. The previous successful result remains visible unless replaced by a later success.

## Detail State

If `detail_available` is true, the `Lihat Detail` action remains visible. For Week 2 it shows a prepared message:

```text
Detail transaksi akan tersedia pada tahap berikutnya.
```

Full evidence/detail UI is deferred to Week 3.

## Deferred Polish

Final visual polish and proportional sizing are deferred to the finishing phase. Week 2 focuses on clear result layers, state handling, and non-broken interactions.
