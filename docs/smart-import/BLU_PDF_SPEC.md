# Blu PDF Parser Spec

## Parser Strategy

`BluPdfParser` is the first provider-specific implementation under the generic Smart Import architecture.

The parser reads the PDF text line-by-line, tracks the current Blu section header, then groups transaction lines into blocks that begin with a transaction datetime. Each block is converted into a standardized transaction object.

This keeps provider-specific parsing logic isolated inside one parser class while reusing the same `BaseParser` contract as future providers.

## Review Group Concept

`review_group` is parser metadata derived from Blu section headers.

Examples:

- `bluAccount` -> `bluAccount`
- `bluSpending - Belanja Bulanan` -> `Belanja Bulanan`
- `bluSpending - Makan Bulanan` -> `Makan Bulanan`

The active review group remains in effect until another section header appears.

`review_group` is not a final category:

- it must not be treated as category prediction
- it must not be persisted into the final transaction table
- it is only intended to help future import review flows

## Parser Output Schema

The parser returns:

```json
{
  "provider": "blu",
  "transactions": [
    {
      "datetime": "16/06/2026 08:30",
      "merchant": "Fore Coffee",
      "amount": 28000,
      "direction": "expense",
      "transaction_type": "DB",
      "review_group": "Makan Bulanan",
      "raw_text": "16/06/2026 08:30 Fore Coffee Rp28.000 DB"
    }
  ]
}
```

Field notes:

- `datetime`: extracted as-is from the PDF text
- `merchant`: raw merchant string from the transaction block
- `amount`: numeric amount parsed from Blu amount text
- `direction`: `expense` for debit, `income` for incoming credit
- `transaction_type`: original payment direction marker such as `DB` or `CR`
- `review_group`: section-derived parser metadata
- `raw_text`: original transaction block text for debugging and review

## Future Extensibility

This parser is the reference implementation for future providers because it demonstrates:

- provider-specific parser class inheritance from `BaseParser`
- standardized output schema
- section-aware metadata extraction
- parser-only metadata without persistence coupling

Future providers such as BCA PDF, SeaBank PDF, GoPay PDF, and OCR-based imports can follow the same pattern while implementing their own text extraction and transaction grouping rules.
