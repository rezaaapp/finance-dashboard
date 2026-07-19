from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from psycopg.rows import dict_row

from app.imports.provider_registry import list_import_provider_configs


DEFAULT_REPAIR_MONTH = "2026-06"


@dataclass(frozen=True)
class ReconciliationScope:
    start_date: date
    end_date: date
    label: str


@dataclass(frozen=True)
class RepairStatement:
    name: str
    sql: str
    params: tuple[Any, ...]


def _sql_literal(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _provider_source_origin_case(provider_expression: str, fallback_expression: str) -> str:
    clauses = " ".join(
        (
            f"when {_sql_literal(provider.key)} then "
            f"{_sql_literal(provider.source_origin)}"
        )
        for provider in list_import_provider_configs()
    )
    return (
        "case lower(btrim(coalesce("
        f"{provider_expression}, ''))) {clauses} "
        f"else {fallback_expression} end"
    )


def _owner_name_expr(table_alias: str | None = None) -> str:
    prefix = f"{table_alias}." if table_alias else ""
    user_name_expr = f"{prefix}user_name"
    raw_name_expr = f"{prefix}raw_payload->>'Nama'"

    return f"""
        case
            when lower(
                btrim(
                    coalesce(
                        nullif({user_name_expr}, ''),
                        nullif({raw_name_expr}, ''),
                        ''
                    )
                )
            ) in ('reza putra pratama', 'reza') then 'Reza'
            else coalesce(
                nullif({user_name_expr}, ''),
                nullif({raw_name_expr}, ''),
                'Unknown'
            )
        end
    """


def _parse_iso_date(value: str | date | None) -> date | None:
    if value is None or value == "":
        return None

    if isinstance(value, date):
        return value

    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _parse_month_scope(value: str | None) -> ReconciliationScope | None:
    if not value:
        return None

    parsed_month = datetime.strptime(value, "%Y-%m").date()
    start_date = parsed_month.replace(day=1)

    if start_date.month == 12:
        next_month = start_date.replace(year=start_date.year + 1, month=1, day=1)
    else:
        next_month = start_date.replace(month=start_date.month + 1, day=1)

    end_date = next_month.fromordinal(next_month.toordinal() - 1)

    return ReconciliationScope(
        start_date=start_date,
        end_date=end_date,
        label=start_date.strftime("%B %Y"),
    )


def resolve_reconciliation_scope(
    *,
    month: str | None = None,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
) -> ReconciliationScope:
    explicit_month_scope = _parse_month_scope(month)

    parsed_date_from = _parse_iso_date(date_from)
    parsed_date_to = _parse_iso_date(date_to)

    if explicit_month_scope and (parsed_date_from or parsed_date_to):
        raise ValueError("Use either --month or --date-from/--date-to, not both.")

    if explicit_month_scope:
        return explicit_month_scope

    if parsed_date_from or parsed_date_to:
        if not parsed_date_from or not parsed_date_to:
            raise ValueError("--date-from and --date-to must be provided together.")

        if parsed_date_from > parsed_date_to:
            raise ValueError("--date-from must be on or before --date-to.")

        return ReconciliationScope(
            start_date=parsed_date_from,
            end_date=parsed_date_to,
            label=f"{parsed_date_from.isoformat()} to {parsed_date_to.isoformat()}",
        )

    return _parse_month_scope(DEFAULT_REPAIR_MONTH)  # type: ignore[return-value]


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def _fetch_all(connection, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, params)
        return [_serialize_value(row) for row in cursor.fetchall()]


def _fetch_one(connection, sql: str, params: tuple[Any, ...]) -> dict[str, Any]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone() or {}
        return _serialize_value(row)


def build_repair_statements(
    *,
    workspace_id: str,
    scope: ReconciliationScope,
) -> list[RepairStatement]:
    start_date = scope.start_date
    end_date = scope.end_date
    import_job_source_origin = _provider_source_origin_case(
        "(select jobs.provider from public.import_jobs as jobs "
        "where jobs.id = transactions.import_job_id)",
        "source_origin",
    )
    payload_source_origin = _provider_source_origin_case(
        "raw_payload->>'_import_provider'",
        "source_origin",
    )

    return [
        RepairStatement(
            name="normalize_reza_owner_names",
            sql="""
                update public.transactions
                set user_name = 'Reza'
                where workspace_id = %s
                  and transaction_date between %s and %s
                  and lower(btrim(coalesce(user_name, ''))) in ('reza putra pratama', 'reza')
            """,
            params=(workspace_id, start_date, end_date),
        ),
        RepairStatement(
            name="backfill_blu_import_owner",
            sql="""
                update public.transactions as transactions
                set user_name = case
                    when lower(btrim(jobs.statement_owner)) in ('reza putra pratama', 'reza') then 'Reza'
                    else jobs.statement_owner
                end
                from public.import_jobs as jobs
                where transactions.workspace_id = %s
                  and transactions.transaction_date between %s and %s
                  and transactions.import_job_id = jobs.id
                  and transactions.source_origin = 'blu_pdf'
                  and nullif(btrim(transactions.user_name), '') is null
                  and nullif(btrim(jobs.statement_owner), '') is not null
            """,
            params=(workspace_id, start_date, end_date),
        ),
        RepairStatement(
            name="backfill_owner_from_raw_payload",
            sql="""
                update public.transactions
                set user_name = case
                    when lower(btrim(raw_payload->>'Nama')) in ('reza putra pratama', 'reza') then 'Reza'
                    else nullif(btrim(raw_payload->>'Nama'), '')
                end
                where workspace_id = %s
                  and transaction_date between %s and %s
                  and nullif(btrim(user_name), '') is null
                  and nullif(btrim(raw_payload->>'Nama'), '') is not null
            """,
            params=(workspace_id, start_date, end_date),
        ),
        RepairStatement(
            name="backfill_source_origin_and_reference",
            sql=f"""
                update public.transactions as transactions
                set
                  source_origin = case
                    when import_job_id is not null then {import_job_source_origin}
                    when import_transaction_fingerprint is not null then {payload_source_origin}
                    else 'google_sheet'
                  end,
                  source_reference = case
                    when import_job_id is not null and import_transaction_fingerprint is not null then
                      concat('import_job:', import_job_id::text, '|fingerprint:', import_transaction_fingerprint)
                    when sheet_source_id is not null and external_row_key is not null then
                      concat('sheet_source:', sheet_source_id::text, '|row:', external_row_key)
                    else source_reference
                  end
                where workspace_id = %s
                  and transaction_date between %s and %s
                  and (
                    nullif(btrim(source_origin), '') is null
                    or nullif(btrim(source_reference), '') is null
                  )
            """,
            params=(workspace_id, start_date, end_date),
        ),
        RepairStatement(
            name="backfill_canonical_fingerprint",
            sql=f"""
                update public.transactions
                set canonical_fingerprint = encode(
                  digest(
                    concat_ws(
                      '|',
                      lower({_owner_name_expr()}),
                      case
                        when transaction_time is not null then to_char(transaction_time, 'YYYY-MM-DD"T"HH24:MI')
                        when transaction_date is not null then to_char(transaction_date, 'YYYY-MM-DD')
                        else ''
                      end,
                      lower(regexp_replace(coalesce(nullif(btrim(title), ''), ''), '\\s+', ' ', 'g')),
                      trim(to_char(amount, 'FM999999999999999990D00')),
                      lower(coalesce(nullif(btrim(direction), ''), '')),
                      lower(coalesce(nullif(btrim(source_fund), ''), ''))
                    ),
                    'sha256'
                  ),
                  'hex'
                )
                where workspace_id = %s
                  and transaction_date between %s and %s
                  and transaction_date is not null
                  and nullif(btrim(canonical_fingerprint), '') is null
            """,
            params=(workspace_id, start_date, end_date),
        ),
        RepairStatement(
            name="backfill_canonical_fingerprint_date",
            sql=f"""
                update public.transactions
                set canonical_fingerprint_date = encode(
                  digest(
                    concat_ws(
                      '|',
                      lower({_owner_name_expr()}),
                      coalesce(to_char(transaction_date, 'YYYY-MM-DD'), ''),
                      lower(regexp_replace(coalesce(nullif(btrim(title), ''), ''), '\\s+', ' ', 'g')),
                      trim(to_char(amount, 'FM999999999999999990D00')),
                      lower(coalesce(nullif(btrim(direction), ''), '')),
                      lower(coalesce(nullif(btrim(source_fund), ''), ''))
                    ),
                    'sha256'
                  ),
                  'hex'
                )
                where workspace_id = %s
                  and transaction_date between %s and %s
                  and transaction_date is not null
                  and nullif(btrim(canonical_fingerprint_date), '') is null
            """,
            params=(workspace_id, start_date, end_date),
        ),
    ]


def apply_reconciliation_repairs(
    connection,
    *,
    workspace_id: str,
    scope: ReconciliationScope,
) -> list[dict[str, Any]]:
    applied_changes: list[dict[str, Any]] = []

    for statement in build_repair_statements(workspace_id=workspace_id, scope=scope):
        with connection.cursor() as cursor:
            cursor.execute(statement.sql, statement.params)
            applied_changes.append(
                {
                    "statement": statement.name,
                    "affected_rows": cursor.rowcount,
                }
            )

    connection.commit()
    return applied_changes


def generate_reconciliation_report(
    connection,
    *,
    workspace_id: str,
    scope: ReconciliationScope,
) -> dict[str, Any]:
    june_summary = _fetch_one(
        connection,
        """
            select
              count(*) as total_transactions,
              count(*) filter (where source_origin = 'blu_pdf') as blu_pdf_transactions,
              count(*) filter (where source_origin = 'google_sheet') as google_sheet_transactions,
              count(*) filter (where nullif(btrim(coalesce(user_name, raw_payload->>'Nama')), '') is null) as unknown_owner_rows,
              count(*) filter (where nullif(btrim(source_origin), '') is null) as missing_source_origin_rows,
              count(*) filter (where nullif(btrim(canonical_fingerprint), '') is null) as missing_canonical_fingerprint_rows,
              count(*) filter (where nullif(btrim(canonical_fingerprint_date), '') is null) as missing_canonical_fingerprint_date_rows
            from public.transactions
            where workspace_id = %s
              and transaction_date between %s and %s
        """,
        (workspace_id, scope.start_date, scope.end_date),
    )

    june_owner_distribution = _fetch_all(
        connection,
        f"""
            select
              {_owner_name_expr()} as owner,
              count(*) as transaction_count,
              coalesce(sum(amount), 0)::numeric(18, 2) as total_amount
            from public.transactions
            where workspace_id = %s
              and transaction_date between %s and %s
            group by 1
            order by transaction_count desc, owner asc
        """,
        (workspace_id, scope.start_date, scope.end_date),
    )

    june_source_origin_distribution = _fetch_all(
        connection,
        """
            select
              coalesce(nullif(btrim(source_origin), ''), 'Unknown') as source_origin,
              count(*) as transaction_count,
              coalesce(sum(amount), 0)::numeric(18, 2) as total_amount
            from public.transactions
            where workspace_id = %s
              and transaction_date between %s and %s
            group by 1
            order by transaction_count desc, source_origin asc
        """,
        (workspace_id, scope.start_date, scope.end_date),
    )

    june_duplicate_candidates = _fetch_all(
        connection,
        f"""
            with scoped as (
              select
                coalesce(canonical_fingerprint_date, canonical_fingerprint) as candidate_key,
                transaction_date,
                source_origin,
                {_owner_name_expr()} as owner,
                title,
                amount,
                created_at
              from public.transactions
              where workspace_id = %s
                and transaction_date between %s and %s
                and coalesce(canonical_fingerprint_date, canonical_fingerprint) is not null
            )
            select
              candidate_key,
              count(*) as duplicate_count,
              count(*) filter (where source_origin = 'blu_pdf') as blu_pdf_count,
              count(*) filter (where source_origin = 'google_sheet') as google_sheet_count,
              array_agg(
                concat_ws(
                  ' | ',
                  coalesce(source_origin, 'Unknown'),
                  coalesce(to_char(transaction_date, 'YYYY-MM-DD'), ''),
                  owner,
                  title,
                  trim(to_char(amount, 'FM999999999999999990D00'))
                )
                order by created_at asc
              ) as sample_rows
            from scoped
            group by candidate_key
            having count(*) > 1
               and count(*) filter (where source_origin = 'blu_pdf') > 0
               and count(*) filter (where source_origin = 'google_sheet') > 0
            order by duplicate_count desc, candidate_key asc
            limit 50
        """,
        (workspace_id, scope.start_date, scope.end_date),
    )

    june_missing_records = _fetch_all(
        connection,
        f"""
            with scoped as (
              select
                coalesce(canonical_fingerprint_date, canonical_fingerprint) as candidate_key,
                transaction_date,
                {_owner_name_expr()} as owner,
                title,
                amount,
                source_origin
              from public.transactions
              where workspace_id = %s
                and transaction_date between %s and %s
                and coalesce(canonical_fingerprint_date, canonical_fingerprint) is not null
            ),
            grouped as (
              select
                candidate_key,
                min(transaction_date) as transaction_date,
                min(owner) as owner,
                min(title) as sample_title,
                max(amount)::numeric(18, 2) as sample_amount,
                bool_or(source_origin = 'blu_pdf') as has_blu_pdf,
                bool_or(source_origin = 'google_sheet') as has_google_sheet
              from scoped
              group by candidate_key
            )
            select
              candidate_key,
              transaction_date,
              owner,
              sample_title,
              sample_amount,
              case
                when has_blu_pdf and not has_google_sheet then 'missing_in_google_sheet'
                when has_google_sheet and not has_blu_pdf then 'missing_in_blu_pdf'
                else 'balanced'
              end as missing_side
            from grouped
            where has_blu_pdf <> has_google_sheet
            order by transaction_date asc nulls last, sample_title asc
            limit 100
        """,
        (workspace_id, scope.start_date, scope.end_date),
    )

    june_dashboard_vs_sql_comparison = _fetch_one(
        connection,
        """
            with scoped as (
              select
                id,
                amount,
                direction,
                source_origin,
                created_at,
                coalesce(canonical_fingerprint_date, canonical_fingerprint, id::text) as candidate_key
              from public.transactions
              where workspace_id = %s
                and transaction_date between %s and %s
            ),
            ranked as (
              select
                *,
                row_number() over (
                  partition by candidate_key
                  order by case when source_origin = 'google_sheet' then 0 else 1 end, created_at asc
                ) as canonical_rank
              from scoped
            )
            select
              count(*) as dashboard_row_count,
              coalesce(sum(case when direction = 'expense' then amount else 0 end), 0)::numeric(18, 2) as dashboard_expense_total,
              coalesce(sum(case when direction = 'income' then amount else 0 end), 0)::numeric(18, 2) as dashboard_income_total,
              count(*) filter (where canonical_rank = 1) as canonical_row_count,
              coalesce(sum(case when canonical_rank = 1 and direction = 'expense' then amount else 0 end), 0)::numeric(18, 2) as canonical_expense_total,
              coalesce(sum(case when canonical_rank = 1 and direction = 'income' then amount else 0 end), 0)::numeric(18, 2) as canonical_income_total
            from ranked
        """,
        (workspace_id, scope.start_date, scope.end_date),
    )

    historical_data_quality_notes = _fetch_one(
        connection,
        """
            with historical as (
              select *
              from public.transactions
              where workspace_id = %s
                and transaction_date is not null
                and transaction_date not between %s and %s
            ),
            duplicate_candidates as (
              select coalesce(canonical_fingerprint_date, canonical_fingerprint) as candidate_key
              from historical
              where coalesce(canonical_fingerprint_date, canonical_fingerprint) is not null
              group by 1
              having count(*) > 1
                 and count(*) filter (where source_origin = 'blu_pdf') > 0
                 and count(*) filter (where source_origin = 'google_sheet') > 0
            )
            select
              (select count(*) from historical) as historical_transactions,
              (select count(*) from historical where nullif(btrim(coalesce(user_name, raw_payload->>'Nama')), '') is null) as historical_unknown_owner_rows,
              (select count(*) from historical where nullif(btrim(source_origin), '') is null) as historical_missing_source_origin_rows,
              (select count(*) from historical where nullif(btrim(canonical_fingerprint), '') is null) as historical_missing_canonical_fingerprint_rows,
              (select count(*) from duplicate_candidates) as historical_duplicate_candidate_groups
        """,
        (workspace_id, scope.start_date, scope.end_date),
    )

    all_time_context = _fetch_one(
        connection,
        """
            select
              count(*) as total_transactions,
              count(*) filter (where source_origin = 'blu_pdf') as blu_pdf_transactions,
              count(*) filter (where source_origin = 'google_sheet') as google_sheet_transactions,
              count(*) filter (where transaction_date between %s and %s) as scoped_transactions
            from public.transactions
            where workspace_id = %s
        """,
        (scope.start_date, scope.end_date, workspace_id),
    )

    repair_plan = [
        {
            "statement": statement.name,
            "params": [
                _serialize_value(statement.params[0]),
                _serialize_value(statement.params[1]),
                _serialize_value(statement.params[2]),
            ],
            "sql": " ".join(statement.sql.split()),
        }
        for statement in build_repair_statements(workspace_id=workspace_id, scope=scope)
    ]

    return {
        "scope": {
            "label": scope.label,
            "start_date": scope.start_date.isoformat(),
            "end_date": scope.end_date.isoformat(),
        },
        "all_time_context": all_time_context,
        "june_db_summary": june_summary,
        "june_owner_distribution": june_owner_distribution,
        "june_source_origin_distribution": june_source_origin_distribution,
        "june_duplicate_candidates": june_duplicate_candidates,
        "june_missing_records": june_missing_records,
        "june_dashboard_vs_sql_comparison": june_dashboard_vs_sql_comparison,
        "historical_data_quality_notes": historical_data_quality_notes,
        "repair_plan": repair_plan,
    }


def format_reconciliation_report(report: dict[str, Any]) -> str:
    scope = report["scope"]
    summary = report["june_db_summary"]
    dashboard_comparison = report["june_dashboard_vs_sql_comparison"]
    historical = report["historical_data_quality_notes"]

    lines = [
        f"Reconciliation Scope: {scope['label']} ({scope['start_date']} to {scope['end_date']})",
        "",
        "June DB Summary",
        f"- Total rows: {summary['total_transactions']}",
        f"- Blu PDF rows: {summary['blu_pdf_transactions']}",
        f"- Google Sheet rows: {summary['google_sheet_transactions']}",
        f"- Unknown/null owner rows: {summary['unknown_owner_rows']}",
        f"- Missing source_origin rows: {summary['missing_source_origin_rows']}",
        f"- Missing canonical_fingerprint rows: {summary['missing_canonical_fingerprint_rows']}",
        f"- Missing canonical_fingerprint_date rows: {summary['missing_canonical_fingerprint_date_rows']}",
        "",
        "June Owner Distribution",
    ]

    owner_distribution = report["june_owner_distribution"] or []
    if owner_distribution:
        lines.extend(
            f"- {row['owner']}: {row['transaction_count']} rows / {row['total_amount']}"
            for row in owner_distribution
        )
    else:
        lines.append("- No June transactions found.")

    lines.extend(
        [
            "",
            "June Source Origin Distribution",
        ]
    )
    source_distribution = report["june_source_origin_distribution"] or []
    if source_distribution:
        lines.extend(
            f"- {row['source_origin']}: {row['transaction_count']} rows / {row['total_amount']}"
            for row in source_distribution
        )
    else:
        lines.append("- No June source rows found.")

    lines.extend(
        [
            "",
            "June Duplicate Candidates",
        ]
    )
    duplicates = report["june_duplicate_candidates"] or []
    if duplicates:
        lines.extend(
            f"- {row['candidate_key']}: {row['duplicate_count']} rows "
            f"(Blu={row['blu_pdf_count']}, Sheet={row['google_sheet_count']})"
            for row in duplicates
        )
    else:
        lines.append("- No June cross-source duplicate candidates found.")

    lines.extend(
        [
            "",
            "June Missing Records",
        ]
    )
    missing_records = report["june_missing_records"] or []
    if missing_records:
        lines.extend(
            f"- {row['transaction_date']} | {row['owner']} | {row['sample_title']} -> {row['missing_side']}"
            for row in missing_records
        )
    else:
        lines.append("- No June missing source records found.")

    lines.extend(
        [
            "",
            "June Dashboard vs SQL Comparison",
            f"- Dashboard row count: {dashboard_comparison['dashboard_row_count']}",
            f"- Canonical row count: {dashboard_comparison['canonical_row_count']}",
            f"- Dashboard expense total: {dashboard_comparison['dashboard_expense_total']}",
            f"- Canonical expense total: {dashboard_comparison['canonical_expense_total']}",
            f"- Dashboard income total: {dashboard_comparison['dashboard_income_total']}",
            f"- Canonical income total: {dashboard_comparison['canonical_income_total']}",
            "",
            "Historical Data Quality Notes",
            f"- Historical rows: {historical['historical_transactions']}",
            f"- Historical unknown/null owner rows: {historical['historical_unknown_owner_rows']}",
            f"- Historical missing source_origin rows: {historical['historical_missing_source_origin_rows']}",
            f"- Historical missing canonical_fingerprint rows: {historical['historical_missing_canonical_fingerprint_rows']}",
            f"- Historical duplicate candidate groups: {historical['historical_duplicate_candidate_groups']}",
            "- No repair action is generated for historical rows outside the scoped window.",
            "",
            "Repair Plan",
        ]
    )

    repair_plan = report["repair_plan"] or []
    if repair_plan:
        lines.extend(
            f"- {row['statement']} (workspace_id={row['params'][0]}, date_from={row['params'][1]}, date_to={row['params'][2]})"
            for row in repair_plan
        )
    else:
        lines.append("- No scoped repair statements generated.")

    return "\n".join(lines)
