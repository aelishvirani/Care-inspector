import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)


from backend.app.database import (
    DATA_DIR,
)


DATABASE = (
    DATA_DIR
    / "care_inspector.db"
)


COLUMNS = {
    "category":
        "VARCHAR",
    "outcome":
        "VARCHAR",
    "method":
        "VARCHAR",
    "path":
        "VARCHAR",
    "status_code":
        "INTEGER",
    "ip_address":
        "VARCHAR",
    "old_value":
        "VARCHAR",
    "new_value":
        "VARCHAR",
    "error_message":
        "VARCHAR",
}


with sqlite3.connect(
    DATABASE
) as conn:

    existing = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(audit_logs)"
        )
    }

    for name, sql_type in (
        COLUMNS.items()
    ):
        if name in existing:
            continue

        conn.execute(
            f"""
            ALTER TABLE audit_logs
            ADD COLUMN {name} {sql_type}
            """
        )

        print(
            f"Added audit_logs.{name}"
        )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_audit_logs_category
        ON audit_logs(category)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_audit_logs_outcome
        ON audit_logs(outcome)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_audit_logs_path
        ON audit_logs(path)
        """
    )

    conn.commit()


print(
    "✓ Audit database upgrade complete"
)
