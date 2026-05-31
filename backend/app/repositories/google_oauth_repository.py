from psycopg.rows import dict_row


def upsert_google_oauth_connection(
    connection,
    *,
    workspace_id: str,
    user_id: str,
    google_email: str,
    access_token_encrypted: str,
    refresh_token_encrypted: str | None,
    token_expiry,
    scopes: str,
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
                google_email.lower(),
                access_token_encrypted,
                refresh_token_encrypted,
                token_expiry,
                scopes,
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
        cursor.execute(
            """
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
            where workspace_id = %s
              and (%s is null or user_id = %s)
              and status = 'active'
            order by updated_at desc
            limit 1
            """,
            (workspace_id, user_id, user_id),
        )

        return cursor.fetchone()


def get_google_oauth_connection_status(
    connection,
    *,
    workspace_id: str,
    user_id: str | None = None,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                workspace_id,
                user_id,
                google_email,
                status,
                updated_at
            from google_oauth_connections
            where workspace_id = %s
              and (%s is null or user_id = %s)
              and status = 'active'
            order by updated_at desc
            limit 1
            """,
            (workspace_id, user_id, user_id),
        )

        return cursor.fetchone()


def disconnect_google_oauth_connection(
    connection,
    *,
    workspace_id: str,
    user_id: str | None = None,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update google_oauth_connections
            set
                status = 'disconnected',
                access_token_encrypted = null,
                refresh_token_encrypted = null,
                updated_at = now()
            where workspace_id = %s
              and (%s is null or user_id = %s)
              and status = 'active'
            returning
                id,
                workspace_id,
                user_id,
                google_email,
                status,
                updated_at
            """,
            (workspace_id, user_id, user_id),
        )

        return cursor.fetchone()
