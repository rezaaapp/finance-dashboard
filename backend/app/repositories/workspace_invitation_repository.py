from psycopg.rows import dict_row


def normalize_invitation_email(email: str) -> str:
    return str(email or "").strip().lower()


def create_workspace_invitation(
    connection,
    *,
    workspace_id: str,
    email: str,
    role: str,
    invited_by_user_id: str,
):
    normalized_email = normalize_invitation_email(email)

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into workspace_invitations (
                workspace_id,
                email,
                role,
                invited_by_user_id,
                invited_user_id
            )
            values (
                %s,
                %s,
                %s,
                %s,
                (
                    select id
                    from users
                    where lower(email::text) = %s
                    limit 1
                )
            )
            returning
                id,
                workspace_id,
                email,
                role,
                status,
                invited_by_user_id,
                invited_user_id,
                expires_at,
                responded_at,
                created_at,
                updated_at
            """,
            (
                workspace_id,
                normalized_email,
                role,
                invited_by_user_id,
                normalized_email,
            ),
        )

        return cursor.fetchone()


def get_pending_invitations_for_email(connection, *, email: str, user_id: str | None = None):
    normalized_email = normalize_invitation_email(email)

    with connection.cursor(row_factory=dict_row) as cursor:
        if user_id:
            cursor.execute(
                """
                update workspace_invitations
                set invited_user_id = %s
                where status = 'pending'
                  and lower(email) = %s
                  and invited_user_id is null
                """,
                (user_id, normalized_email),
            )

        cursor.execute(
            """
            select
                wi.id,
                wi.workspace_id,
                w.name as workspace_name,
                wi.email,
                wi.role,
                wi.status,
                wi.invited_by_user_id,
                inviter.name as invited_by_name,
                inviter.email as invited_by_email,
                wi.expires_at,
                wi.responded_at,
                wi.created_at,
                wi.updated_at
            from workspace_invitations wi
            inner join workspaces w on w.id = wi.workspace_id
            inner join users inviter on inviter.id = wi.invited_by_user_id
            where wi.status = 'pending'
              and lower(wi.email) = %s
            order by wi.created_at desc
            """,
            (normalized_email,),
        )

        return cursor.fetchall()


def get_pending_invitations_for_workspace(connection, *, workspace_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                wi.id,
                wi.workspace_id,
                wi.email,
                wi.role,
                wi.status,
                wi.invited_by_user_id,
                inviter.name as invited_by_name,
                inviter.email as invited_by_email,
                wi.invited_user_id,
                wi.expires_at,
                wi.responded_at,
                wi.created_at,
                wi.updated_at
            from workspace_invitations wi
            inner join users inviter on inviter.id = wi.invited_by_user_id
            where wi.workspace_id = %s
              and wi.status = 'pending'
            order by wi.created_at desc
            """,
            (workspace_id,),
        )

        return cursor.fetchall()


def get_invitation_by_id(connection, *, invitation_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                wi.id,
                wi.workspace_id,
                w.name as workspace_name,
                wi.email,
                wi.role,
                wi.status,
                wi.invited_by_user_id,
                wi.invited_user_id,
                wi.expires_at,
                wi.responded_at,
                wi.created_at,
                wi.updated_at
            from workspace_invitations wi
            inner join workspaces w on w.id = wi.workspace_id
            where wi.id = %s
            limit 1
            """,
            (invitation_id,),
        )

        return cursor.fetchone()


def accept_invitation(connection, *, invitation_id: str, user_id: str, email: str):
    normalized_email = normalize_invitation_email(email)

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update workspace_invitations
            set
                status = 'accepted',
                invited_user_id = %s,
                responded_at = now()
            where id = %s
              and status = 'pending'
              and lower(email) = %s
            returning
                id,
                workspace_id,
                email,
                role,
                status,
                invited_by_user_id,
                invited_user_id,
                expires_at,
                responded_at,
                created_at,
                updated_at
            """,
            (user_id, invitation_id, normalized_email),
        )

        return cursor.fetchone()


def decline_invitation(connection, *, invitation_id: str, user_id: str, email: str):
    normalized_email = normalize_invitation_email(email)

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update workspace_invitations
            set
                status = 'declined',
                invited_user_id = coalesce(invited_user_id, %s),
                responded_at = now()
            where id = %s
              and status = 'pending'
              and lower(email) = %s
            returning
                id,
                workspace_id,
                email,
                role,
                status,
                invited_by_user_id,
                invited_user_id,
                expires_at,
                responded_at,
                created_at,
                updated_at
            """,
            (user_id, invitation_id, normalized_email),
        )

        return cursor.fetchone()


def cancel_invitation(connection, *, workspace_id: str, invitation_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update workspace_invitations
            set
                status = 'cancelled',
                responded_at = now()
            where id = %s
              and workspace_id = %s
              and status = 'pending'
            returning
                id,
                workspace_id,
                email,
                role,
                status,
                invited_by_user_id,
                invited_user_id,
                expires_at,
                responded_at,
                created_at,
                updated_at
            """,
            (invitation_id, workspace_id),
        )

        return cursor.fetchone()


def has_pending_invitation(connection, *, workspace_id: str, email: str) -> bool:
    normalized_email = normalize_invitation_email(email)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            select 1
            from workspace_invitations
            where workspace_id = %s
              and lower(email) = %s
              and status = 'pending'
            limit 1
            """,
            (workspace_id, normalized_email),
        )

        return cursor.fetchone() is not None


def is_active_workspace_member(connection, *, workspace_id: str, user_id: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select 1
            from workspace_members
            where workspace_id = %s
              and user_id = %s
            limit 1
            """,
            (workspace_id, user_id),
        )

        return cursor.fetchone() is not None


def is_active_workspace_member_by_email(connection, *, workspace_id: str, email: str):
    normalized_email = normalize_invitation_email(email)

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                wm.id,
                wm.workspace_id,
                wm.user_id,
                wm.role,
                u.email,
                u.name
            from workspace_members wm
            inner join users u on u.id = wm.user_id
            where wm.workspace_id = %s
              and lower(u.email::text) = %s
            limit 1
            """,
            (workspace_id, normalized_email),
        )

        return cursor.fetchone()


def add_workspace_member_if_missing(
    connection,
    *,
    workspace_id: str,
    user_id: str,
    role: str,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into workspace_members (workspace_id, user_id, role)
            values (%s, %s, %s)
            on conflict (workspace_id, user_id)
            do nothing
            returning id, workspace_id, user_id, role, created_at, updated_at
            """,
            (workspace_id, user_id, role),
        )
        member = cursor.fetchone()

        if member:
            return member

        cursor.execute(
            """
            select id, workspace_id, user_id, role, created_at, updated_at
            from workspace_members
            where workspace_id = %s
              and user_id = %s
            limit 1
            """,
            (workspace_id, user_id),
        )

        return cursor.fetchone()
