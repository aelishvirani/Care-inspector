from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

QUEUE_DB = (
    PROJECT_ROOT
    / "data"
    / "collector_queue.db"
)


class OfflineQueue:
    def __init__(
        self,
        path: Path = QUEUE_DB,
    ):
        self.path = path

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()


    def _connect(
        self,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path
        )

        connection.row_factory = (
            sqlite3.Row
        )

        return connection


    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS
                pending_measurements (
                    id INTEGER PRIMARY KEY
                        AUTOINCREMENT,

                    payload TEXT NOT NULL,

                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            db.commit()


    def enqueue(
        self,
        measurement: dict[str, Any],
    ) -> int:
        payload = json.dumps(
            measurement
        )

        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO
                    pending_measurements
                    (payload)
                VALUES
                    (?)
                """,
                (payload,),
            )

            db.commit()

            return int(
                cursor.lastrowid
            )


    def get_pending(
        self,
        limit: int = 100,
    ) -> list[
        tuple[
            int,
            dict[str, Any],
        ]
    ]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT
                    id,
                    payload
                FROM
                    pending_measurements
                ORDER BY
                    id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            (
                int(row["id"]),
                json.loads(
                    row["payload"]
                ),
            )
            for row in rows
        ]


    def delete(
        self,
        queue_id: int,
    ) -> None:
        with self._connect() as db:
            db.execute(
                """
                DELETE FROM
                    pending_measurements
                WHERE
                    id = ?
                """,
                (queue_id,),
            )

            db.commit()


    def count(self) -> int:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT COUNT(*)
                AS total
                FROM
                    pending_measurements
                """
            ).fetchone()

        return int(
            row["total"]
        )
