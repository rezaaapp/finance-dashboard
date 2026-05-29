from datetime import datetime
from typing import Optional

from psycopg.rows import dict_row


def upsert_user(connection, *, email: str, name: str, avatar_url: Optional[str]):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into users (email, name, avatar_url)
            values (%s, %s, %s)
            on conflict (email)
            do update set
                name = excluded.name,
                avatar_url = coalesce(excluded.avatar_url, users.avatar_url)
            returning id, email, name, avatar_url, created_at, updated_at
            """,
            (email.lower(), name, avatar_url),
        )

        return cursor.fetchone()


def upsert_user_tokens(
    connection,
    *,
    user_id: str,
    access_token: str,
    refresh_token: Optional[str],
    token_expires_at: datetime,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        if refresh_token:
            cursor.execute(
                """
                insert into user_tokens (
                    user_id,
                    access_token,
                    refresh_token,
                    token_expires_at
                )
                values (%s, %s, %s, %s)
                on conflict (user_id)
                do update set
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    token_expires_at = excluded.token_expires_at
                returning id, user_id, token_expires_at, created_at, updated_at
                """,
                (user_id, access_token, refresh_token, token_expires_at),
            )
        else:
            cursor.execute(
                """
                update user_tokens
                set
                    access_token = %s,
                    token_expires_at = %s
                where user_id = %s
                returning id, user_id, token_expires_at, created_at, updated_at
                """,
                (access_token, token_expires_at, user_id),
            )

            if cursor.rowcount == 0:
                raise ValueError(
                    "Google did not return a refresh_token. Revoke consent and retry OAuth."
                )

        return cursor.fetchone()
