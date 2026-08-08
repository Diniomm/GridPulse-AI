"""Persistence contracts plus in-memory and SQLite implementations."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol

from .domain import Asset, Incident


class IncidentRepository(Protocol):
    def save_asset(self, asset: Asset) -> Asset: ...

    def get_asset(self, asset_id: str) -> Asset | None: ...

    def save_incident(self, incident: Incident) -> Incident: ...

    def get_incident(self, incident_id: str) -> Incident | None: ...

    def list_incidents(self) -> tuple[Incident, ...]: ...


class InMemoryIncidentRepository:
    """Small deterministic repository used before the database is introduced."""

    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}
        self._incidents: dict[str, Incident] = {}

    def save_asset(self, asset: Asset) -> Asset:
        self._assets[asset.asset_id] = asset
        return asset

    def get_asset(self, asset_id: str) -> Asset | None:
        return self._assets.get(asset_id)

    def save_incident(self, incident: Incident) -> Incident:
        self._incidents[incident.incident_id] = incident
        return incident

    def get_incident(self, incident_id: str) -> Incident | None:
        return self._incidents.get(incident_id)

    def list_incidents(self) -> tuple[Incident, ...]:
        return tuple(self._incidents.values())


@dataclass(frozen=True, slots=True)
class ReportRecord:
    incident_id: str
    incident_title: str
    status: str
    report: dict[str, object]
    reviewer_reason: str | None
    updated_at: str


class SQLiteIncidentRepository:
    """Small local repository that survives application restarts."""

    def __init__(self, path: str | Path = "data/gridpulse.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.commit()
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS reports (
                    incident_id TEXT PRIMARY KEY,
                    incident_title TEXT,
                    status TEXT NOT NULL,
                    report TEXT NOT NULL,
                    reviewer_reason TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
                );
                """
            )
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(reports)").fetchall()
            }
            if "incident_title" not in columns:
                connection.execute("ALTER TABLE reports ADD COLUMN incident_title TEXT")

    def save_incident(self, incident: Incident) -> Incident:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO incidents (incident_id, payload, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(incident_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (incident.incident_id, json.dumps(incident.to_dict())),
            )
        return incident

    def get_incident_payload(self, incident_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM incidents WHERE incident_id = ?", (incident_id,)
            ).fetchone()
        return json.loads(row["payload"]) if row else None

    def save_report(
        self,
        incident_id: str,
        *,
        incident_title: str | None = None,
        status: str,
        report: dict[str, object],
        reviewer_reason: str | None = None,
    ) -> ReportRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reports (incident_id, incident_title, status, report, reviewer_reason, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(incident_id) DO UPDATE SET
                    incident_title = COALESCE(excluded.incident_title, reports.incident_title),
                    status = excluded.status,
                    report = excluded.report,
                    reviewer_reason = excluded.reviewer_reason,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (incident_id, incident_title, status, json.dumps(report), reviewer_reason),
            )
            row = connection.execute(
                "SELECT reports.incident_id, reports.incident_title, reports.status, reports.report, "
                "reports.reviewer_reason, reports.updated_at FROM reports WHERE reports.incident_id = ?",
                (incident_id,),
            ).fetchone()
        return _report_from_row(row)

    def list_reports(self) -> tuple[ReportRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT reports.incident_id, reports.incident_title, reports.status, reports.report, "
                "reports.reviewer_reason, reports.updated_at, incidents.payload AS incident_payload "
                "FROM reports LEFT JOIN incidents ON reports.incident_id = incidents.incident_id "
                "ORDER BY reports.updated_at DESC, reports.incident_id DESC"
            ).fetchall()
        return tuple(_report_from_row(row) for row in rows)

    def delete_report(self, incident_id: str) -> bool:
        with self._connect() as connection:
            report = connection.execute(
                "DELETE FROM reports WHERE incident_id = ?", (incident_id,)
            )
            connection.execute("DELETE FROM incidents WHERE incident_id = ?", (incident_id,))
        return report.rowcount > 0


def _report_from_row(row: sqlite3.Row) -> ReportRecord:
    title = row["incident_title"]
    if not title and row.keys() and "incident_payload" in row.keys() and row["incident_payload"]:
        title = json.loads(row["incident_payload"]).get("title")
    return ReportRecord(
        incident_id=row["incident_id"],
        incident_title=title or row["incident_id"],
        status=row["status"],
        report=json.loads(row["report"]),
        reviewer_reason=row["reviewer_reason"],
        updated_at=row["updated_at"],
    )
