from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from agent.trip import SEED_VERSION, TRIP_ID, TRIPS, seed_segments_for, segment_from_dict, segment_to_dict

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def seed_body(trip_id: str = TRIP_ID) -> dict[str, Any]:
    try:
        trip = TRIPS[trip_id]
    except KeyError:
        raise KeyError(f"unknown trip {trip_id}") from None
    return {
        "version": SEED_VERSION,
        "id": trip_id,
        "member_id": trip["member_id"],
        "passenger": trip["passenger"],
        "segments": [segment_to_dict(segment) for segment in seed_segments_for(trip_id)],
        "hotel": trip["hotel"],
    }


class ConciergeDb:
    def __init__(self, url: str) -> None:
        self.url = url

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self.url, row_factory=dict_row)

    def apply_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
            for trip_id in TRIPS:
                conn.execute(
                    """
                    INSERT INTO concierge.snapshots (trip_id, body)
                    VALUES (%s, %s)
                    ON CONFLICT (trip_id) DO NOTHING
                    """,
                    (trip_id, json.dumps(seed_body(trip_id))),
                )
            conn.commit()

    def snapshot(self, trip_id: str = TRIP_ID) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT body FROM concierge.snapshots WHERE trip_id = %s",
                (trip_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError(f"trip snapshot missing: {trip_id}")
        return json.loads(row["body"])

    def save_snapshot(self, trip_id: str, body: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO concierge.snapshots (trip_id, body)
                VALUES (%s, %s)
                ON CONFLICT (trip_id) DO UPDATE SET body = EXCLUDED.body
                """,
                (trip_id, json.dumps(body)),
            )
            conn.commit()

    def reset(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM concierge.case_events")
            conn.execute("DELETE FROM concierge.cases")
            conn.execute("DELETE FROM concierge.notifications")
            for trip_id in TRIPS:
                conn.execute(
                    """
                    INSERT INTO concierge.snapshots (trip_id, body)
                    VALUES (%s, %s)
                    ON CONFLICT (trip_id) DO UPDATE SET body = EXCLUDED.body
                    """,
                    (trip_id, json.dumps(seed_body(trip_id))),
                )
            conn.commit()

    def insert_case(self, case_id: str, trip_id: str, state: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO concierge.cases (id, trip_id, state) VALUES (%s, %s, %s)",
                (case_id, trip_id, state),
            )
            conn.commit()

    def save_case(self, case_id: str, state: str, events: list[dict[str, Any]], trip_id: str = TRIP_ID) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE concierge.cases SET state = %s WHERE id = %s", (state, case_id))
            for event in events:
                conn.execute(
                    """
                    INSERT INTO concierge.case_events (case_id, state, event, detail)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (case_id, event["state"], event["event"], json.dumps(event["detail"])),
                )
                if event["event"] == "notified":
                    conn.execute(
                        "INSERT INTO concierge.notifications (trip_id, message) VALUES (%s, %s)",
                        (trip_id, event["detail"].get("message", "")),
                    )
            conn.commit()

    def latest_case(self, trip_id: str | None = None) -> dict[str, Any] | None:
        with self._connect() as conn:
            if trip_id is None:
                return conn.execute(
                    """
                    SELECT id, trip_id, state, created_at
                    FROM concierge.cases
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ).fetchone()
            return conn.execute(
                """
                SELECT id, trip_id, state, created_at
                FROM concierge.cases
                WHERE trip_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (trip_id,),
            ).fetchone()

    def recent_cases(self, limit: int = 10, trip_id: str | None = None) -> list[dict[str, Any]]:
        """Disruption inbox: past cases with final state, newest first."""
        with self._connect() as conn:
            if trip_id is None:
                rows = conn.execute(
                    """
                    SELECT id, trip_id, state, created_at
                    FROM concierge.cases
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, trip_id, state, created_at
                    FROM concierge.cases
                    WHERE trip_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (trip_id, limit),
                ).fetchall()
        return [
            {
                "id": row["id"],
                "trip_id": row["trip_id"],
                "state": row["state"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]

    def append_event(self, case_id: str, event: dict[str, Any], trip_id: str = TRIP_ID) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE concierge.cases SET state = %s WHERE id = %s", (event["state"], case_id))
            conn.execute(
                """
                INSERT INTO concierge.case_events (case_id, state, event, detail)
                VALUES (%s, %s, %s, %s)
                """,
                (case_id, event["state"], event["event"], json.dumps(event["detail"])),
            )
            if event["event"] == "notified":
                conn.execute(
                    "INSERT INTO concierge.notifications (trip_id, message) VALUES (%s, %s)",
                    (trip_id, event["detail"].get("message", "")),
                )
            conn.commit()

    def events(self, case_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, state, event, detail, created_at
                FROM concierge.case_events
                WHERE case_id = %s
                ORDER BY id ASC
                """,
                (case_id,),
            ).fetchall()
        parsed = []
        for row in rows:
            parsed.append(
                {
                    "id": row["id"],
                    "state": row["state"],
                    "event": row["event"],
                    "detail": json.loads(row["detail"]),
                    "created_at": row["created_at"].isoformat(),
                }
            )
        return parsed

    def notifications(self, trip_id: str = TRIP_ID) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, message, created_at
                FROM concierge.notifications
                WHERE trip_id = %s
                ORDER BY id ASC
                """,
                (trip_id,),
            ).fetchall()
        return [
            {"id": row["id"], "message": row["message"], "created_at": row["created_at"].isoformat()}
            for row in rows
        ]


def segments_from_body(body: dict[str, Any]):
    return [segment_from_dict(raw) for raw in body["segments"]]
