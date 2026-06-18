class IncrementalImportEngine:
    def apply(
        self,
        transactions: list[dict],
        *,
        existing_fingerprints: set[str],
        fingerprint_statuses: dict[str, str] | None = None,
    ) -> list[dict]:
        incremental_transactions = []
        fingerprint_statuses = fingerprint_statuses or {}

        for transaction in transactions:
            transaction_fingerprint = str(transaction.get("transaction_fingerprint", ""))
            incremental_transactions.append({
                **transaction,
                "is_existing": bool(
                    transaction.get("is_existing", False)
                    or transaction_fingerprint in existing_fingerprints
                ),
                "registry_status": (
                    transaction.get("registry_status")
                    or fingerprint_statuses.get(transaction_fingerprint)
                ),
            })

        return incremental_transactions
