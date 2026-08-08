"""Demo-mode composition root for the Streamlit application."""

from __future__ import annotations

from datetime import datetime, timezone

from .fixtures import demo_incidents
from .hazards import parse_nws_alerts
from .multimodal import MediaProcessor
from .rag import HybridIndex, ManualIngestor
from .workflow import InvestigationWorkflow


DEMO_MANUAL = """# Storm Inspection Guide

## Page 1

Storm response begins with scene safety. Treat every downed or visibly damaged conductor as energized until qualified personnel verify isolation. Establish a safe perimeter before approaching the asset.

## Page 2

For a leaning wooden pole, inspect the foundation, guy wires, crossarm attachment points, insulators, conductor clearance, and nearby vegetation. Photograph each damaged component.

## Page 3

For a split or fractured crossarm after high winds, keep the line out of service until a qualified crew evaluates conductor tension and hardware.

## Page 4

Escalate immediately when a conductor is down near a public road, school, hospital, fire, or active work zone. If evidence is ambiguous, request a physical inspection instead of guessing.
"""


def build_demo_workflow() -> InvestigationWorkflow:
    index = HybridIndex()
    chunks = ManualIngestor().ingest_text(
        DEMO_MANUAL,
        document_id="storm-inspection-guide",
        title="Storm Inspection Guide",
        source_uri="demo://storm-inspection-guide",
    )
    index.add(chunks)
    alert = parse_nws_alerts(
        {
            "features": [
                {
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-94.60, 39.08], [-94.55, 39.08], [-94.55, 39.12]]],
                    },
                    "properties": {
                        "id": "demo:nws:wind-1",
                        "event": "High Wind Warning",
                        "headline": "High Wind Warning — demo fixture",
                        "onset": "2026-08-07T14:00:00Z",
                        "expires": "2026-08-07T18:00:00Z",
                        "severity": "Severe",
                    },
                }
            ]
        }
    )
    return InvestigationWorkflow(
        index,
        media=MediaProcessor(),
        hazard_loader=lambda _incident: alert,
    )


def demo_incident_options() -> dict[str, object]:
    return {incident.incident_id: incident for incident in demo_incidents()}

