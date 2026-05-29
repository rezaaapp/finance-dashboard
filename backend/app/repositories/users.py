from datetime import datetime
from typing import Optional

from psycopg.rows import dict_row


def upsert_user(
    connection,
    *,
    email: str,
    name: str,
    avatar_url: Optional[str],
    role: str = "user",
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into users (email, name, avatar_url, role)
            values (%s, %s, %s, %s)
            on conflict (email)
            do update set
                name = excluded.name,
                avatar_url = coalesce(excluded.avatar_url, users.avatar_url),
                role = case
                    when excluded.role = 'super_admin' then 'super_admin'
                    else users.role
                end
            returning id, email, name, avatar_url, role, created_at, updated_at
            """,
            (email.lower(), name, avatar_url, role),
        )

        return cursor.fetchone()


def list_users(connection):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                email,
                name,
                avatar_url,
                role,
                created_at,
                updated_at
            from users
            order by
                case when role = 'super_admin' then 0 else 1 end,
                case when role = 'owner' then 0 else 1 end,
                case when role = 'member' then 0 else 1 end,
                created_at desc
            """
        )

        return cursor.fetchall()


def get_user_by_id(connection, *, user_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                email,
                name,
                avatar_url,
                role,
                created_at,
                updated_at
            from users
            where id = %s
            """,
            (user_id,),
        )

        return cursor.fetchone()


def upsert_invited_member_user(connection, *, email: str, name: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into users (email, name, avatar_url, role)
            values (%s, %s, null, 'member')
            on conflict (email)
            do update set
                name = coalesce(nullif(excluded.name, ''), users.name),
                role = case
                    when users.role in ('super_admin', 'owner') then users.role
                    else 'member'
                end
            returning id, email, name, avatar_url, role, created_at, updated_at
            """,
            (email.lower(), name),
        )

        return cursor.fetchone()


def create_user(
    connection,
    *,
    email: str,
    name: str,
    role: str,
    avatar_url: Optional[str] = None,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into users (email, name, avatar_url, role)
            values (%s, %s, %s, %s)
            returning id, email, name, avatar_url, role, created_at, updated_at
            """,
            (email.lower(), name, avatar_url, role),
        )

        return cursor.fetchone()


def update_user(connection, *, user_id: str, email: str, name: str, role: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update users
            set
                email = %s,
                name = %s,
                role = %s
            where id = %s
            returning id, email, name, avatar_url, role, created_at, updated_at
            """,
            (email.lower(), name, role, user_id),
        )

        return cursor.fetchone()


def update_user_role(connection, *, user_id: str, role: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update users
            set role = %s
            where id = %s
            returning id, email, name, avatar_url, role, created_at, updated_at
            """,
            (role, user_id),
        )

        return cursor.fetchone()


def delete_user(connection, *, user_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            delete from users
            where id = %s
            returning id, email, name, avatar_url, role, created_at, updated_at
            """,
            (user_id,),
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
