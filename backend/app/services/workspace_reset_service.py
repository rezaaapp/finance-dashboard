RESET_TABLES = (
    ("transactions", "delete from transactions where workspace_id = %s"),
    ("import_jobs", "delete from import_jobs where workspace_id = %s"),
    (
        "fingerprint_registry",
        "delete from import_transaction_registry where workspace_id = %s",
    ),
    ("budgets", "delete from budgets where workspace_id = %s"),
    (
        "budget_category_ignores",
        "delete from budget_category_ignores where workspace_id = %s",
    ),
    ("sync_history", "delete from sync_jobs where workspace_id = %s"),
)


def reset_google_sheet_synced_data(
    connection, *, workspace_id: str, source_id: str,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            delete from transactions
            where workspace_id = %s
              and sheet_source_id = %s
              and source_origin = 'google_sheet'
            """,
            (workspace_id, source_id),
        )
        return cursor.rowcount or 0


def factory_reset_workspace_data(connection, *, workspace_id: str) -> dict[str, int]:
    deleted = {}
    with connection.cursor() as cursor:
        for entity, statement in RESET_TABLES:
            cursor.execute(statement, (workspace_id,))
            deleted[entity] = cursor.rowcount or 0
    return deleted
