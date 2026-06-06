from psycopg.rows import dict_row


def create_google_sheet_source(
    connection,
    *,
    workspace_id: str,
    oauth_connection_id: str,
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
            if existing_source["status"] != "disabled":
                return None

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
    oauth_connection_id: str,
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
