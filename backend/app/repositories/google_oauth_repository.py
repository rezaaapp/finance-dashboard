from psycopg.rows import dict_row


def _normalize_scopes(scopes: str | list[str] | tuple[str, ...]):
    if isinstance(scopes, str):
        return [scope for scope in scopes.split() if scope]

    return list(scopes or [])


def upsert_google_oauth_connection(
    connection,
    *,
    workspace_id: str,
    user_id: str,
    google_email: str | None,
    access_token_encrypted: str,
    refresh_token_encrypted: str | None,
    token_expiry,
    scopes: str | list[str] | tuple[str, ...],
    status: str = "active",
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into google_oauth_connections (
                workspace_id,
                user_id,
                google_email,
                access_token_encrypted,
                refresh_token_encrypted,
                token_expiry,
                scopes,
                status
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (workspace_id, user_id)
            do update set
                google_email = excluded.google_email,
                access_token_encrypted = excluded.access_token_encrypted,
                refresh_token_encrypted = coalesce(
                    excluded.refresh_token_encrypted,
                    google_oauth_connections.refresh_token_encrypted
                ),
                token_expiry = excluded.token_expiry,
                scopes = excluded.scopes,
                status = excluded.status,
                updated_at = now()
            returning
                id,
                workspace_id,
                user_id,
                google_email,
                token_expiry,
                scopes,
                status,
                created_at,
                updated_at
            """,
            (
                workspace_id,
                user_id,
                google_email.lower() if google_email else None,
                access_token_encrypted,
                refresh_token_encrypted,
                token_expiry,
                _normalize_scopes(scopes),
                status,
            ),
        )

        return cursor.fetchone()


def get_active_google_oauth_connection(
    connection,
    *,
    workspace_id: str,
    user_id: str | None = None,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        if user_id:
            where_clause = """
            where workspace_id = %s
              and user_id = %s
              and status = 'active'
            """
            params = (workspace_id, user_id)
        else:
            where_clause = """
            where workspace_id = %s
              and status = 'active'
            """
            params = (workspace_id,)

        cursor.execute(
            f"""
            select
                id,
                workspace_id,
                user_id,
                google_email,
                access_token_encrypted,
                refresh_token_encrypted,
                token_expiry,
                scopes,
                status,
                created_at,
                updated_at
            from google_oauth_connections
            {where_clause}
            order by updated_at desc
            limit 1
            """,
            params,
        )

        return cursor.fetchone()


def get_google_oauth_connection_status(
    connection,
    *,
    workspace_id: str,
    user_id: str | None = None,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        if user_id:
            where_clause = """
            where workspace_id = %s
              and user_id = %s
              and status = 'active'
            """
            params = (workspace_id, user_id)
        else:
            where_clause = """
            where workspace_id = %s
              and status = 'active'
            """
            params = (workspace_id,)

        cursor.execute(
            f"""
            select
                id,
                workspace_id,
                user_id,
                google_email,
                status,
                updated_at
            from google_oauth_connections
            {where_clause}
            order by updated_at desc
            limit 1
            """,
            params,
        )

        return cursor.fetchone()


def disconnect_google_oauth_connection(
    connection,
    *,
    workspace_id: str,
    user_id: str | None = None,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        if user_id:
            where_clause = """
            where workspace_id = %s
              and user_id = %s
              and status = 'active'
            """
            params = (workspace_id, user_id)
        else:
            where_clause = """
            where workspace_id = %s
              and status = 'active'
            """
            params = (workspace_id,)

        cursor.execute(
            f"""
            update google_oauth_connections
            set
                status = 'disconnected',
                access_token_encrypted = null,
                refresh_token_encrypted = null,
                updated_at = now()
            {where_clause}
            returning
                id,
                workspace_id,
                user_id,
                google_email,
                status,
                updated_at
            """,
            params,
        )

        return cursor.fetchone()
