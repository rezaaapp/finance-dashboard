import json

from psycopg.rows import dict_row


def get_google_sheet_source_tab_preferences(connection, *, workspace_id: str, source_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "select google_sheet_sources from workspace_configurations where workspace_id = %s",
            (workspace_id,),
        )
        row = cursor.fetchone() or {}
    for item in row.get("google_sheet_sources") or []:
        if str(item.get("source_id") or item.get("id") or "") == str(source_id):
            return {
                "selected_tabs": list(item.get("selected_tabs") or []),
                "default_tab": item.get("default_tab"),
            }
    return {"selected_tabs": [], "default_tab": None}


def save_google_sheet_source_tab_preferences(
    connection, *, workspace_id: str, source_id: str,
    selected_tabs: list[str], default_tab: str | None,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "select google_sheet_sources from workspace_configurations where workspace_id = %s",
            (workspace_id,),
        )
        row = cursor.fetchone() or {}
        sources = list(row.get("google_sheet_sources") or [])
        preference = {
            "id": str(source_id),
            "source_id": str(source_id),
            "label": "Google Sheet source",
            "status": "active",
            "selected_tabs": list(dict.fromkeys(selected_tabs)),
            "default_tab": default_tab,
        }
        for index, item in enumerate(sources):
            if str(item.get("source_id") or item.get("id") or "") == str(source_id):
                sources[index] = {**item, **preference}
                break
        else:
            sources.append(preference)
        cursor.execute(
            """
            insert into workspace_configurations (workspace_id, google_sheet_sources)
            values (%s, %s::jsonb)
            on conflict (workspace_id) do update
            set google_sheet_sources = excluded.google_sheet_sources, updated_at = now()
            """,
            (workspace_id, json.dumps(sources)),
        )


def create_google_sheet_source(
    connection,
    *,
    workspace_id: str,
    oauth_connection_id: str | None,
    sheet_id: str,
    sheet_url: str,
    spreadsheet_title: str | None,
    sheet_name: str | None,
    year: int | None,
    status: str = "active",
):
    with connection.cursor(row_factory=dict_row) as cursor:
        existing_source = _get_existing_source_for_key(
            cursor,
            workspace_id=workspace_id,
            sheet_id=sheet_id,
            year=year,
        )

        if existing_source:
            return reactivate_google_sheet_source(
                cursor,
                workspace_id=workspace_id,
                source_id=str(existing_source["id"]),
                oauth_connection_id=oauth_connection_id,
                sheet_url=sheet_url,
                spreadsheet_title=spreadsheet_title,
                sheet_name=sheet_name,
                status=status,
            )

        cursor.execute(
            """
            insert into google_sheet_sources (
                workspace_id,
                oauth_connection_id,
                sheet_id,
                sheet_url,
                spreadsheet_title,
                sheet_name,
                year,
                status
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (workspace_id, sheet_id, year)
            do nothing
            returning
                id,
                workspace_id,
                oauth_connection_id,
                sheet_id,
                sheet_url,
                spreadsheet_title,
                sheet_name,
                year,
                status,
                last_synced_at,
                created_at,
                updated_at
            """,
            (
                workspace_id,
                oauth_connection_id,
                sheet_id,
                sheet_url,
                spreadsheet_title,
                sheet_name,
                year,
                status,
            ),
        )

        return cursor.fetchone()


def _get_existing_source_for_key(cursor, *, workspace_id: str, sheet_id: str, year: int | None):
    year_filter = "year is null" if year is None else "year = %s"
    params = (workspace_id, sheet_id) if year is None else (workspace_id, sheet_id, year)

    cursor.execute(
        f"""
        select
            id,
            workspace_id,
            oauth_connection_id,
            sheet_id,
            sheet_url,
            spreadsheet_title,
            sheet_name,
            year,
            status,
            last_synced_at,
            created_at,
            updated_at
        from google_sheet_sources
        where workspace_id = %s
          and sheet_id = %s
          and {year_filter}
        limit 1
        """,
        params,
    )

    return cursor.fetchone()


def reactivate_google_sheet_source(
    cursor,
    *,
    workspace_id: str,
    source_id: str,
    oauth_connection_id: str | None,
    sheet_url: str,
    spreadsheet_title: str | None,
    sheet_name: str | None,
    status: str,
):
    cursor.execute(
        """
        update google_sheet_sources
        set
            oauth_connection_id = %s,
            sheet_url = %s,
            spreadsheet_title = %s,
            sheet_name = %s,
            status = %s,
            updated_at = now()
        where workspace_id = %s
          and id = %s
        returning
            id,
            workspace_id,
            oauth_connection_id,
            sheet_id,
            sheet_url,
            spreadsheet_title,
            sheet_name,
            year,
            status,
            last_synced_at,
            created_at,
            updated_at
        """,
        (
            oauth_connection_id,
            sheet_url,
            spreadsheet_title,
            sheet_name,
            status,
            workspace_id,
            source_id,
        ),
    )

    return cursor.fetchone()


def get_google_sheet_sources(connection, *, workspace_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                workspace_id,
                oauth_connection_id,
                sheet_id,
                sheet_url,
                spreadsheet_title,
                sheet_name,
                year,
                status,
                last_synced_at,
                created_at,
                updated_at
            from google_sheet_sources
            where workspace_id = %s
              and status != 'disabled'
            order by year desc nulls last, created_at desc
            """,
            (workspace_id,),
        )

        return cursor.fetchall()


def get_google_sheet_source(
    connection,
    *,
    workspace_id: str,
    source_id: str,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                workspace_id,
                oauth_connection_id,
                sheet_id,
                sheet_url,
                spreadsheet_title,
                sheet_name,
                year,
                status,
                last_synced_at,
                created_at,
                updated_at
            from google_sheet_sources
            where workspace_id = %s
              and id = %s
            """,
            (workspace_id, source_id),
        )

        return cursor.fetchone()


def get_google_sheet_source_by_id(connection, *, source_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                workspace_id,
                oauth_connection_id,
                sheet_id,
                sheet_url,
                spreadsheet_title,
                sheet_name,
                year,
                status,
                last_synced_at,
                created_at,
                updated_at
            from google_sheet_sources
            where id = %s
            """,
            (source_id,),
        )

        return cursor.fetchone()


def get_primary_google_sheet_source(connection, *, workspace_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                workspace_id,
                oauth_connection_id,
                sheet_id,
                sheet_url,
                spreadsheet_title,
                sheet_name,
                year,
                status,
                last_synced_at,
                created_at,
                updated_at
            from google_sheet_sources
            where workspace_id = %s
              and status != 'disabled'
            order by year desc nulls last, created_at asc
            limit 1
            """,
            (workspace_id,),
        )

        return cursor.fetchone()


def ensure_import_google_sheet_source(
    connection,
    *,
    workspace_id: str,
    oauth_connection_id: str | None,
    sheet_id: str,
):
    existing_source = get_primary_google_sheet_source(
        connection,
        workspace_id=workspace_id,
    )

    if existing_source:
        return existing_source

    if not str(sheet_id or "").strip():
        return None

    return create_google_sheet_source(
        connection,
        workspace_id=workspace_id,
        oauth_connection_id=oauth_connection_id,
        sheet_id=sheet_id,
        sheet_url=f"https://docs.google.com/spreadsheets/d/{sheet_id}",
        spreadsheet_title="Smart Import Sheet",
        sheet_name="Sheet1",
        year=None,
        status="active",
    )


def update_google_sheet_last_synced(connection, *, workspace_id: str, source_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update google_sheet_sources
            set
                last_synced_at = now(),
                status = 'active',
                updated_at = now()
            where workspace_id = %s
              and id = %s
            returning
                id,
                workspace_id,
                oauth_connection_id,
                sheet_id,
                sheet_url,
                spreadsheet_title,
                sheet_name,
                year,
                status,
                last_synced_at,
                created_at,
                updated_at
            """,
            (workspace_id, source_id),
        )

        return cursor.fetchone()


def mark_google_sheet_source_error(connection, *, workspace_id: str, source_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update google_sheet_sources
            set
                status = 'error',
                updated_at = now()
            where workspace_id = %s
              and id = %s
            returning
                id,
                workspace_id,
                oauth_connection_id,
                sheet_id,
                sheet_url,
                spreadsheet_title,
                sheet_name,
                year,
                status,
                last_synced_at,
                created_at,
                updated_at
            """,
            (workspace_id, source_id),
        )

        return cursor.fetchone()


def delete_google_sheet_source(connection, *, workspace_id: str, source_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update google_sheet_sources
            set
                status = 'disabled',
                updated_at = now()
            where workspace_id = %s
              and id = %s
              and status != 'disabled'
            returning
                id,
                workspace_id,
                oauth_connection_id,
                sheet_id,
                sheet_url,
                spreadsheet_title,
                sheet_name,
                year,
                status,
                last_synced_at,
                created_at,
                updated_at
            """,
            (workspace_id, source_id),
        )

        return cursor.fetchone()
