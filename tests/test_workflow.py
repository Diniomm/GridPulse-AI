import unittest
from datetime import datetime, timezone

from gridpulse.domain import Coordinates, Incident, Observation, ObservationType
from gridpulse.fixtures import demo_incidents
from gridpulse.hazards import parse_nws_alerts
from gridpulse.multimodal import DemoSpeechProvider, DemoVisionProvider, MediaProcessor
from gridpulse.rag import HybridIndex, ManualIngestor
from gridpulse.workflow import InvestigationWorkflow
from gridpulse.langgraph_runtime import build_langgraph_app


MANUAL = """# Storm Manual

## Page 1

Storm safety requires a safe perimeter and a physical inspection before approaching any downed conductor.

## Page 2

For a leaning pole or broken crossarm, inspect the foundation, attachment points, insulators, conductor clearance, and transformer.
"""


def build_index() -> HybridIndex:
    index = HybridIndex()
    chunks = ManualIngestor().ingest_text(
        MANUAL,
        document_id="storm-manual",
        title="Storm Manual",
        source_uri="storm-manual.md",
    )
    index.add(chunks)
    return index


class WorkflowTest(unittest.TestCase):
    def test_langgraph_adapter_is_optional(self) -> None:
        try:
            app = build_langgraph_app(InvestigationWorkflow(build_index()))
        except RuntimeError as error:
            self.assertIn("optional AI dependencies", str(error))
        else:
            self.assertIsNotNone(app)

    def test_demo_incident_produces_cited_reviewable_report(self) -> None:
        alert = parse_nws_alerts(
            {
                "features": [
                    {
                        "geometry": {"coordinates": [[[-94.58, 39.09], [-94.57, 39.11]]]},
                        "properties": {
                            "id": "nws-wind-1",
                            "event": "High Wind Warning",
                            "headline": "High Wind Warning",
                            "onset": "2026-08-07T14:00:00Z",
                            "expires": "2026-08-07T18:00:00Z",
                        },
                    }
                ]
            }
        )
        workflow = InvestigationWorkflow(
            build_index(),
            media=MediaProcessor(DemoVisionProvider(), DemoSpeechProvider()),
            hazard_loader=lambda _incident: alert,
        )
        result = workflow.run(demo_incidents()[0], image_path="storm-pole.jpg", audio_path="storm-pole.wav")
        self.assertTrue(result.requires_human_review)
        self.assertEqual(result.state.hypotheses[0].status.value, "probable")
        self.assertTrue(result.state.report["requires_human_approval"])
        self.assertTrue(any("storm-manual.md" in citation for citation in result.state.report["citations"]))

    def test_human_rejection_requires_reason(self) -> None:
        workflow = InvestigationWorkflow(build_index())
        result = workflow.run(demo_incidents()[1])
        with self.assertRaises(ValueError):
            result.reject(" ")
        result.reject("Need a daylight inspection")
        self.assertEqual(result.state.status, "rejected")

    def test_insufficient_evidence_abstains(self) -> None:
        incident = Incident(
            incident_id="INC-UNKNOWN",
            title="Unknown event",
            description="An interruption was reported with no visible damage.",
            asset_id="POLE-184",
            location=Coordinates(39.0997, -94.5786),
            occurred_at=datetime(2026, 8, 7, 14, 30, tzinfo=timezone.utc),
            observations=(
                Observation(
                    "OBS-UNKNOWN",
                    ObservationType.TEXT,
                    "No additional details available",
                    "operator-note.txt",
                    0.3,
                ),
            ),
        )
        result = InvestigationWorkflow(build_index()).run(incident)
        self.assertEqual(result.state.hypotheses[0].status.value, "insufficient_evidence")
        self.assertIn("additional evidence", result.state.report["recommendation"])
