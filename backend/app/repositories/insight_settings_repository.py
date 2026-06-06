from psycopg.rows import dict_row


SETTING_FIELDS = (
    "need_warning_ratio",
    "need_danger_ratio",
    "want_warning_ratio",
    "want_danger_ratio",
    "saving_warning_ratio",
    "saving_good_ratio",
    "uncategorized_warning_count",
    "uncategorized_danger_count",
    "anomaly_warning_multiplier",
    "anomaly_danger_multiplier",
)


def _serialize_settings(row, *, source: str) -> dict:
    if not row:
        return {}

    serialized = {}

    for field in SETTING_FIELDS:
        value = row[field]

        if field.endswith("_count"):
            serialized[field] = int(value)
        else:
            serialized[field] = float(value)

    serialized["source"] = source
    return serialized


def get_workspace_insight_settings(connection, *, workspace_id: str) -> dict | None:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                need_warning_ratio,
                need_danger_ratio,
                want_warning_ratio,
                want_danger_ratio,
                saving_warning_ratio,
                saving_good_ratio,
                uncategorized_warning_count,
                uncategorized_danger_count,
                anomaly_warning_multiplier,
                anomaly_danger_multiplier
            from workspace_insight_settings
            where workspace_id = %s
            """,
            (workspace_id,),
        )
        row = cursor.fetchone()

    return _serialize_settings(row, source="workspace") if row else None


def get_effective_insight_settings(
    connection,
    *,
    workspace_id: str,
    default_settings: dict,
) -> dict:
    workspace_settings = get_workspace_insight_settings(
        connection,
        workspace_id=workspace_id,
    )

    if workspace_settings:
        return workspace_settings

    return {
        **default_settings,
        "source": "default",
    }


def upsert_workspace_insight_settings(
    connection,
    *,
    workspace_id: str,
    settings_payload: dict,
) -> dict:
    values = [settings_payload[field] for field in SETTING_FIELDS]

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into workspace_insight_settings (
                workspace_id,
                need_warning_ratio,
                need_danger_ratio,
                want_warning_ratio,
                want_danger_ratio,
                saving_warning_ratio,
                saving_good_ratio,
                uncategorized_warning_count,
                uncategorized_danger_count,
                anomaly_warning_multiplier,
                anomaly_danger_multiplier
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (workspace_id)
            do update set
                need_warning_ratio = excluded.need_warning_ratio,
                need_danger_ratio = excluded.need_danger_ratio,
                want_warning_ratio = excluded.want_warning_ratio,
                want_danger_ratio = excluded.want_danger_ratio,
                saving_warning_ratio = excluded.saving_warning_ratio,
                saving_good_ratio = excluded.saving_good_ratio,
                uncategorized_warning_count = excluded.uncategorized_warning_count,
                uncategorized_danger_count = excluded.uncategorized_danger_count,
                anomaly_warning_multiplier = excluded.anomaly_warning_multiplier,
                anomaly_danger_multiplier = excluded.anomaly_danger_multiplier,
                updated_at = now()
            returning
                need_warning_ratio,
                need_danger_ratio,
                want_warning_ratio,
                want_danger_ratio,
                saving_warning_ratio,
                saving_good_ratio,
                uncategorized_warning_count,
                uncategorized_danger_count,
                anomaly_warning_multiplier,
                anomaly_danger_multiplier
            """,
            (workspace_id, *values),
        )
        row = cursor.fetchone()

    return _serialize_settings(row, source="workspace")
