from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import get_migration_connection
from app.services.reconciliation_service import (
    apply_reconciliation_repairs,
    format_reconciliation_report,
    generate_reconciliation_report,
    resolve_reconciliation_scope,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit Smart Import reconciliation and prepare June-scoped repair plan.",
    )
    parser.add_argument("--workspace-id", required=True, help="Target workspace UUID.")
    parser.add_argument("--month", help="Scoped repair month in YYYY-MM format. Defaults to 2026-06.")
    parser.add_argument("--date-from", help="Custom scoped repair start date in YYYY-MM-DD format.")
    parser.add_argument("--date-to", help="Custom scoped repair end date in YYYY-MM-DD format.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply scoped metadata backfills after printing the reviewable report.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the report as JSON instead of a text report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    scope = resolve_reconciliation_scope(
        month=args.month,
        date_from=args.date_from,
        date_to=args.date_to,
    )

    with get_migration_connection() as connection:
        report = generate_reconciliation_report(
            connection,
            workspace_id=args.workspace_id,
            scope=scope,
        )

        if args.apply:
            applied_changes = apply_reconciliation_repairs(
                connection,
                workspace_id=args.workspace_id,
                scope=scope,
            )
            report["applied_changes"] = applied_changes
            report = generate_reconciliation_report(
                connection,
                workspace_id=args.workspace_id,
                scope=scope,
            ) | {"applied_changes": applied_changes}

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    print(format_reconciliation_report(report))
    if args.apply:
        print("")
        print("Applied Changes")
        for change in report.get("applied_changes", []):
            print(f"- {change['statement']}: {change['affected_rows']} rows")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
