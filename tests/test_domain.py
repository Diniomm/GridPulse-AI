import unittest
from datetime import datetime, timezone

from gridpulse.domain import (
    Coordinates,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    Observation,
    ObservationType,
)


class DomainValidationTest(unittest.TestCase):
    def test_coordinates_reject_invalid_latitude(self) -> None:
        with self.assertRaisesRegex(ValueError, "latitude"):
            Coordinates(91, 0)

    def test_observation_rejects_invalid_confidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "confidence"):
            Observation("OBS-1", ObservationType.TEXT, "damage", "note.txt", 1.1)

    def test_evidence_rejects_invalid_page(self) -> None:
        with self.assertRaisesRegex(ValueError, "source_page"):
            Evidence("E-1", "Manual", "Inspect the pole", "manual.pdf", 0)

    def test_hypothesis_accepts_timezone_normalized_evidence(self) -> None:
        hypothesis = Hypothesis(
            cause="wind damage",
            status=HypothesisStatus.PROBABLE,
            confidence=0.8,
            supporting_evidence_ids=("E-1",),
        )
        self.assertEqual(hypothesis.status.value, "probable")

    def test_observation_normalizes_naive_datetime_to_utc(self) -> None:
        observation = Observation(
            "OBS-2",
            ObservationType.TEXT,
            "line down",
            "note.txt",
            0.9,
            datetime(2026, 8, 7, 14, 30),
        )
        self.assertEqual(observation.observed_at.tzinfo, timezone.utc)

