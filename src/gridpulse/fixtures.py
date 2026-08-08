"""Deterministic synthetic records used by demo mode and tests."""

from __future__ import annotations

from datetime import datetime, timezone

from .domain import (
    Asset,
    AssetType,
    Coordinates,
    Incident,
    IncidentSeverity,
    Observation,
    ObservationType,
)


def demo_assets() -> tuple[Asset, ...]:
    return (
        Asset(
            asset_id="POLE-184",
            asset_type=AssetType.POLE,
            name="Pole 184",
            location=Coordinates(39.0997, -94.5786),
            manufacturer="Northline Structures",
            model="NL-WOOD-12",
        ),
        Asset(
            asset_id="SUB-021",
            asset_type=AssetType.SUBSTATION,
            name="Downtown Substation",
            location=Coordinates(39.1041, -94.5844),
            manufacturer="Midwest Grid Systems",
            model="MGS-440",
        ),
    )


def demo_incidents() -> tuple[Incident, ...]:
    occurred_at = datetime(2026, 8, 7, 14, 30, tzinfo=timezone.utc)
    return (
        Incident(
            incident_id="INC-1042",
            title="Storm damage near access road",
            description=(
                "A field technician reports a leaning pole and a broken upper crossarm "
                "after a severe thunderstorm."
            ),
            asset_id="POLE-184",
            location=Coordinates(39.0997, -94.5786),
            occurred_at=occurred_at,
            severity=IncidentSeverity.HIGH,
            observations=(
                Observation(
                    observation_id="OBS-1042-1",
                    observation_type=ObservationType.TEXT,
                    value="Pole is leaning toward the access road.",
                    source="technician-note.txt",
                    confidence=0.94,
                    observed_at=occurred_at,
                ),
                Observation(
                    observation_id="OBS-1042-2",
                    observation_type=ObservationType.VISUAL,
                    value="Upper crossarm appears fractured; transformer appears intact.",
                    source="field-photo-1042.jpg",
                    confidence=0.86,
                    observed_at=occurred_at,
                ),
            ),
        ),
        Incident(
            incident_id="INC-1043",
            title="Possible substation smoke report",
            description="A caller reports smoke east of the substation, but no equipment failure is confirmed.",
            asset_id="SUB-021",
            location=Coordinates(39.1041, -94.5844),
            occurred_at=occurred_at,
            severity=IncidentSeverity.MEDIUM,
            observations=(
                Observation(
                    observation_id="OBS-1043-1",
                    observation_type=ObservationType.TEXT,
                    value="Smoke visible east of the substation; operations appear normal.",
                    source="operator-note.txt",
                    confidence=0.71,
                    observed_at=occurred_at,
                ),
            ),
        ),
    )

