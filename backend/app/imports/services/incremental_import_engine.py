class IncrementalImportEngine:
    def apply(self, transactions: list[dict], *, existing_fingerprints: set[str]) -> list[dict]:
        incremental_transactions = []

        for transaction in transactions:
            transaction_fingerprint = str(transaction.get("transaction_fingerprint", ""))
            incremental_transactions.append({
                **transaction,
                "is_existing": transaction_fingerprint in existing_fingerprints,
            })

        return incremental_transactions
