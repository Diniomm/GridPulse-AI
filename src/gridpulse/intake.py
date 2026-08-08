"""Validated construction of incidents entered through the dashboard."""

from __future__ import annotations

from datetime import datetime, timezone

from .domain import Coordinates, Incident, IncidentSeverity


def build_custom_incident(
    *,
    title: str,
    description: str,
    asset_id: str,
    latitude: float,
    longitude: float,
    severity: str,
) -> Incident:
    """Build a user-entered incident with the same domain validation as fixtures."""

    normalized_title = title.strip()
    normalized_description = description.strip()
    normalized_asset_id = asset_id.strip()
    if not normalized_title or not normalized_description or not normalized_asset_id:
        raise ValueError("title, description, and asset ID are required")
    try:
        incident_severity = IncidentSeverity(severity.lower())
    except ValueError as error:
        raise ValueError("severity must be low, medium, high, or critical") from error

    timestamp = datetime.now(timezone.utc)
    incident_id = f"CUSTOM-{timestamp.strftime('%Y%m%d-%H%M%S')}"
    return Incident(
        incident_id=incident_id,
        title=normalized_title,
        description=normalized_description,
        asset_id=normalized_asset_id,
        location=Coordinates(float(latitude), float(longitude)),
        occurred_at=timestamp,
        severity=incident_severity,
    )
