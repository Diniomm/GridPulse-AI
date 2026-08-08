import unittest

from gridpulse.fixtures import demo_assets, demo_incidents
from gridpulse.storage import InMemoryIncidentRepository


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

