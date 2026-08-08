import unittest
import tempfile
from pathlib import Path

from gridpulse.fixtures import demo_assets, demo_incidents
from gridpulse.storage import InMemoryIncidentRepository, SQLiteIncidentRepository


class FixturesAndStorageTest(unittest.TestCase):
    def test_demo_records_are_linked(self) -> None:
        assets = {asset.asset_id for asset in demo_assets()}
        self.assertGreaterEqual(len(assets), 2)
        self.assertTrue(all(incident.asset_id in assets for incident in demo_incidents()))

    def test_repository_round_trip(self) -> None:
        repository = InMemoryIncidentRepository()
        incident = demo_incidents()[0]
        repository.save_incident(incident)
        self.assertEqual(repository.get_incident(incident.incident_id), incident)
        self.assertEqual(repository.list_incidents(), (incident,))

    def test_sqlite_repository_survives_new_repository_instance(self) -> None:
        incident = demo_incidents()[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gridpulse.db"
            first = SQLiteIncidentRepository(path)
            first.save_incident(incident)
            first.save_report(
                incident.incident_id,
                status="awaiting_review",
                report={"recommendation": "Review evidence"},
            )

            second = SQLiteIncidentRepository(path)
            payload = second.get_incident_payload(incident.incident_id)
            reports = second.list_reports()
            deleted = second.delete_report(incident.incident_id)
            remaining_reports = second.list_reports()

        self.assertIsNotNone(payload)
        self.assertEqual(payload["incident_id"], incident.incident_id)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].status, "awaiting_review")
        self.assertTrue(deleted)
        self.assertEqual(remaining_reports, ())
