from psycopg.rows import dict_row


def _legacy_allocation_type(financial_type: str) -> str:
    if financial_type == "want":
        return "Wants"

    if financial_type == "saving":
        return "Savings"

    return "Needs"


def list_classification_rules(connection, *, workspace_id: str) -> list[dict]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                workspace_id,
                match_type,
                title_pattern,
                raw_category_pattern,
                direction,
                financial_type,
                category,
                confidence_score,
                explanation,
                allocation_type,
                priority,
                is_active,
                created_at,
                updated_at
            from classification_rules
            where workspace_id = %s
            order by is_active desc, priority asc, created_at desc
            """,
            (workspace_id,),
        )

        return cursor.fetchall()


def get_active_classification_rules(connection, *, workspace_id: str) -> list[dict]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                match_type,
                title_pattern,
                raw_category_pattern,
                direction,
                financial_type,
                category,
                confidence_score,
                explanation,
                priority
            from classification_rules
            where workspace_id = %s
              and is_active = true
            order by priority asc, created_at asc
            """,
            (workspace_id,),
        )

        return cursor.fetchall()


def create_classification_rule(
    connection,
    *,
    workspace_id: str,
    match_type: str,
    title_pattern: str,
    raw_category_pattern: str | None,
    direction: str,
    financial_type: str,
    category: str,
    confidence_score: float,
    explanation: str | None,
    priority: int,
    is_active: bool = True,
) -> dict:
    allocation_type = _legacy_allocation_type(financial_type)

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into classification_rules (
                workspace_id,
                match_type,
                title_pattern,
                raw_category_pattern,
                direction,
                financial_type,
                category,
                confidence_score,
                explanation,
                allocation_type,
                priority,
                is_active
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning *
            """,
            (
                workspace_id,
                match_type,
                title_pattern,
                raw_category_pattern,
                direction,
                financial_type,
                category,
                confidence_score,
                explanation,
                allocation_type,
                priority,
                is_active,
            ),
        )

        return cursor.fetchone()


def upsert_classification_rule_for_pattern(
    connection,
    *,
    workspace_id: str,
    match_type: str,
    title_pattern: str,
    raw_category_pattern: str | None,
    direction: str,
    financial_type: str,
    category: str,
    confidence_score: float,
    explanation: str | None,
    priority: int,
    is_active: bool = True,
) -> tuple[dict, bool]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select id
            from classification_rules
            where workspace_id = %s
              and match_type = %s
              and title_pattern = %s
              and coalesce(raw_category_pattern, '') = coalesce(%s, '')
            order by created_at desc
            limit 1
            """,
            (workspace_id, match_type, title_pattern, raw_category_pattern),
        )
        existing = cursor.fetchone()

    if existing:
        rule = update_classification_rule(
            connection,
            workspace_id=workspace_id,
            rule_id=str(existing["id"]),
            match_type=match_type,
            title_pattern=title_pattern,
            raw_category_pattern=raw_category_pattern,
            direction=direction,
            financial_type=financial_type,
            category=category,
            confidence_score=confidence_score,
            explanation=explanation,
            priority=priority,
            is_active=is_active,
        )

        return rule, False

    return create_classification_rule(
        connection,
        workspace_id=workspace_id,
        match_type=match_type,
        title_pattern=title_pattern,
        raw_category_pattern=raw_category_pattern,
        direction=direction,
        financial_type=financial_type,
        category=category,
        confidence_score=confidence_score,
        explanation=explanation,
        priority=priority,
        is_active=is_active,
    ), True


def update_classification_rule(
    connection,
    *,
    workspace_id: str,
    rule_id: str,
    match_type: str,
    title_pattern: str,
    raw_category_pattern: str | None,
    direction: str,
    financial_type: str,
    category: str,
    confidence_score: float,
    explanation: str | None,
    priority: int,
    is_active: bool,
) -> dict | None:
    allocation_type = _legacy_allocation_type(financial_type)

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update classification_rules
            set
                match_type = %s,
                title_pattern = %s,
                raw_category_pattern = %s,
                direction = %s,
                financial_type = %s,
                category = %s,
                confidence_score = %s,
                explanation = %s,
                allocation_type = %s,
                priority = %s,
                is_active = %s,
                updated_at = now()
            where workspace_id = %s
              and id = %s
            returning *
            """,
            (
                match_type,
                title_pattern,
                raw_category_pattern,
                direction,
                financial_type,
                category,
                confidence_score,
                explanation,
                allocation_type,
                priority,
                is_active,
                workspace_id,
                rule_id,
            ),
        )

        return cursor.fetchone()


def delete_classification_rule(
    connection,
    *,
    workspace_id: str,
    rule_id: str,
) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            delete from classification_rules
            where workspace_id = %s
              and id = %s
            """,
            (workspace_id, rule_id),
        )

        return bool(cursor.rowcount)
