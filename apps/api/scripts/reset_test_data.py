#!/usr/bin/env python3
"""Delete application test records while preserving schema and migrations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import engine  # noqa: E402

CONFIRMATION = "DELETE-ALL-TEST-DATA"
TABLES = (
    "onboarding_answers",
    "parent_health_profiles",
    "family_invites",
    "whatsapp_identities",
    "onboarding_sessions",
    "members",
    "families",
)


def table_counts(connection) -> dict[str, int]:
    return {
        table: int(
            connection.execute(
                text(f'SELECT count(*) FROM "{table}"')
            ).scalar_one()
        )
        for table in TABLES
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm",
        help=f"Required exact confirmation: {CONFIRMATION}",
    )
    args = parser.parse_args()

    with engine.begin() as connection:
        before = table_counts(connection)

        if args.confirm != CONFIRMATION:
            print("Dry run only. Existing row counts:")
            for table, count in before.items():
                print(f"  {table}: {count}")
            print(
                "\nNothing was deleted. Re-run with "
                f"--confirm {CONFIRMATION}"
            )
            return 2

        if engine.dialect.name == "postgresql":
            table_list = ", ".join(f'public."{table}"' for table in TABLES)
            connection.execute(
                text(
                    f"TRUNCATE TABLE {table_list} "
                    "RESTART IDENTITY CASCADE"
                )
            )
        else:
            for table in TABLES:
                connection.execute(text(f'DELETE FROM "{table}"'))

        after = table_counts(connection)

    print("Test data deleted. Row counts:")
    for table, count in after.items():
        print(f"  {table}: {count}")
    print("Schema and alembic_version were preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
