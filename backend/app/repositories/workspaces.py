import json

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import settings


def normalize_google_sheet_sources(sources=None, fallback_google_sheet_id=None):
    normalized_sources = []

    if isinstance(sources, str):
        try:
            sources = json.loads(sources)
        except json.JSONDecodeError:
            sources = []

    if isinstance(sources, list):
        for index, source in enumerate(sources):
            if isinstance(source, str):
                source_id = source.strip()
                label = f"Source {index + 1}"
                status = "active"
            elif isinstance(source, dict):
                source_id = str(
                    source.get("id") or source.get("google_sheet_id") or ""
                ).strip()
                label = str(source.get("label") or f"Source {index + 1}").strip()
                status = str(source.get("status") or "active").strip()
            else:
                continue

            if not source_id:
                continue

            if any(existing["id"] == source_id for existing in normalized_sources):
                raise ValueError(f"Google Sheet ID '{source_id}' is already connected.")

            normalized_sources.append({
                "id": source_id,
                "label": label,
                "status": status,
            })

    if not normalized_sources and fallback_google_sheet_id:
        normalized_sources.append({
            "id": fallback_google_sheet_id,
            "label": "Source 1",
            "status": "active",
        })

    if len(normalized_sources) > settings.MAX_GOOGLE_SHEET_SOURCES:
        raise ValueError(
            f"Maximum {settings.MAX_GOOGLE_SHEET_SOURCES} Google Sheet sources are allowed."
        )

    return normalized_sources


def get_primary_workspace_for_user(connection, *, user_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                w.id,
                w.name,
                w.subscription_status,
                wm.role,
                wc.google_sheet_id,
                wc.google_sheet_sources
            from workspaces w
            inner join workspace_members wm on wm.workspace_id = w.id
            left join workspace_configurations wc on wc.workspace_id = w.id
            where wm.user_id = %s
            order by
                case when wm.role = 'owner' then 0 else 1 end,
                w.created_at asc
            limit 1
            """,
            (user_id,),
        )

        return cursor.fetchone()


def create_workspace(connection, *, name: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into workspaces (name, subscription_status)
            values (%s, 'free')
            returning id, name, subscription_status, created_at, updated_at
            """,
            (name,),
        )

        return cursor.fetchone()


def upsert_workspace_member(
    connection,
    *,
    workspace_id: str,
    user_id: str,
    role: str = "owner",
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into workspace_members (workspace_id, user_id, role)
            values (%s, %s, %s)
            on conflict (workspace_id, user_id)
            do update set role = excluded.role
            returning id, workspace_id, user_id, role, created_at, updated_at
            """,
            (workspace_id, user_id, role),
        )

        return cursor.fetchone()


def upsert_workspace_configuration(
    connection,
    *,
    workspace_id: str,
    google_sheet_id: str | None = None,
    google_sheet_sources=None,
):
    normalized_sources = normalize_google_sheet_sources(
        google_sheet_sources,
        google_sheet_id,
    )
    primary_google_sheet_id = normalized_sources[0]["id"] if normalized_sources else None

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into workspace_configurations (
                workspace_id,
                google_sheet_id,
                google_sheet_sources
            )
            values (%s, %s, %s)
            on conflict (workspace_id)
            do update set
                google_sheet_id = excluded.google_sheet_id,
                google_sheet_sources = excluded.google_sheet_sources
            returning
                id,
                workspace_id,
                google_sheet_id,
                google_sheet_sources,
                created_at,
                updated_at
            """,
            (workspace_id, primary_google_sheet_id, Jsonb(normalized_sources)),
        )

        return cursor.fetchone()


def ensure_default_workspace_for_user(
    connection,
    *,
    user_id: str,
    user_name: str,
):
    existing_workspace = get_primary_workspace_for_user(
        connection,
        user_id=user_id,
    )

    if existing_workspace:
        upsert_workspace_configuration(
            connection,
            workspace_id=str(existing_workspace["id"]),
        )
        return existing_workspace

    workspace = create_workspace(
        connection,
        name=f"{user_name}'s Household",
    )
    upsert_workspace_member(
        connection,
        workspace_id=str(workspace["id"]),
        user_id=user_id,
        role="owner",
    )
    configuration = upsert_workspace_configuration(
        connection,
        workspace_id=str(workspace["id"]),
    )

    return {
        **workspace,
        "role": "owner",
        "google_sheet_id": configuration["google_sheet_id"],
        "google_sheet_sources": configuration["google_sheet_sources"],
    }


def update_google_sheet_id_for_user(
    connection,
    *,
    user_id: str,
    google_sheet_id: str | None,
    google_sheet_sources=None,
):
    workspace = get_primary_workspace_for_user(
        connection,
        user_id=user_id,
    )

    if not workspace:
        raise ValueError("Workspace not found for this user")

    configuration = upsert_workspace_configuration(
        connection,
        workspace_id=str(workspace["id"]),
        google_sheet_id=google_sheet_id,
        google_sheet_sources=google_sheet_sources,
    )

    return {
        **workspace,
        "google_sheet_id": configuration["google_sheet_id"],
        "google_sheet_sources": configuration["google_sheet_sources"],
    }
