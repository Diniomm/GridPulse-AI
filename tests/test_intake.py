import unittest

from gridpulse.intake import build_custom_incident


class CustomIntakeTest(unittest.TestCase):
    def test_builds_valid_custom_incident(self) -> None:
        incident = build_custom_incident(
            title="Leaning pole near road",
            description="The pole is leaning after high winds.",
            asset_id="POLE-900",
            latitude=39.1,
            longitude=-94.5,
            severity="high",
        )
        self.assertTrue(incident.incident_id.startswith("CUSTOM-"))
        self.assertEqual(incident.severity.value, "high")

    def test_rejects_missing_required_text(self) -> None:
        with self.assertRaises(ValueError):
            build_custom_incident(
                title=" ",
                description="Description",
                asset_id="POLE-900",
                latitude=39.1,
                longitude=-94.5,
                severity="medium",
            )

    def test_rejects_unknown_severity(self) -> None:
        with self.assertRaises(ValueError):
            build_custom_incident(
                title="Incident",
                description="Description",
                asset_id="POLE-900",
                latitude=39.1,
                longitude=-94.5,
                severity="urgent",
            )
