from psycopg.rows import dict_row


def create_password_credential(connection, *, user_id: str, password_hash: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into user_password_credentials (user_id, password_hash)
            values (%s, %s)
            returning user_id, created_at, updated_at
            """,
            (user_id, password_hash),
        )
        return cursor.fetchone()


def get_password_login_user(connection, *, email: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                u.id,
                u.email,
                u.name,
                u.avatar_url,
                u.role,
                u.created_at,
                u.updated_at,
                credential.password_hash
            from users u
            inner join user_password_credentials credential
              on credential.user_id = u.id
            where u.email = %s
            limit 1
            """,
            (email.strip().lower(),),
        )
        return cursor.fetchone()
