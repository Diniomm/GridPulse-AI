"""Typed domain objects for GridPulse incidents.

The MVP keeps these objects dependency-free so demo mode can run before any
external model, database, or API credentials are configured.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class AssetType(StrEnum):
    POLE = "pole"
    TRANSFORMER = "transformer"
    SUBSTATION = "substation"
    CONDUCTOR = "conductor"


class IncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    NEW = "new"
    INVESTIGATING = "investigating"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ObservationType(StrEnum):
    TEXT = "text"
    VISUAL = "visual"
    AUDIO = "audio"
    WEATHER = "weather"
    SEISMIC = "seismic"
    TELEMETRY = "telemetry"


class HypothesisStatus(StrEnum):
    POSSIBLE = "possible"
    PROBABLE = "probable"
    CONFIRMED = "confirmed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class Coordinates:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")


@dataclass(frozen=True, slots=True)
class Asset:
    asset_id: str
    asset_type: AssetType
    name: str
    location: Coordinates
    manufacturer: str | None = None
    model: str | None = None

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise ValueError("asset_id cannot be empty")
        if not self.name.strip():
            raise ValueError("asset name cannot be empty")


@dataclass(frozen=True, slots=True)
class Observation:
    observation_id: str
    observation_type: ObservationType
    value: str
    source: str
    confidence: float
    observed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("observation_id cannot be empty")
        if not self.value.strip():
            raise ValueError("observation value cannot be empty")
        if not self.source.strip():
            raise ValueError("observation source cannot be empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("observation confidence must be between 0 and 1")
        if self.observed_at is not None:
            object.__setattr__(self, "observed_at", _ensure_utc(self.observed_at))


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    title: str
    content: str
    source_uri: str
    source_page: int | None = None
    relevance_score: float | None = None

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id cannot be empty")
        if not self.title.strip() or not self.content.strip():
            raise ValueError("evidence title and content cannot be empty")
        if not self.source_uri.strip():
            raise ValueError("evidence source_uri cannot be empty")
        if self.source_page is not None and self.source_page < 1:
            raise ValueError("source_page must be positive")
        if self.relevance_score is not None and not 0 <= self.relevance_score <= 1:
            raise ValueError("relevance_score must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class Hypothesis:
    cause: str
    status: HypothesisStatus
    confidence: float
    supporting_evidence_ids: tuple[str, ...] = ()
    contradicting_evidence_ids: tuple[str, ...] = ()
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.cause.strip():
            raise ValueError("hypothesis cause cannot be empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("hypothesis confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class Incident:
    incident_id: str
    title: str
    description: str
    asset_id: str
    location: Coordinates
    occurred_at: datetime
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.NEW
    observations: tuple[Observation, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()

    def __post_init__(self) -> None:
        if not self.incident_id.strip():
            raise ValueError("incident_id cannot be empty")
        if not self.title.strip() or not self.description.strip():
            raise ValueError("incident title and description cannot be empty")
        if not self.asset_id.strip():
            raise ValueError("incident asset_id cannot be empty")
        object.__setattr__(self, "occurred_at", _ensure_utc(self.occurred_at))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation for APIs and persistence."""

        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "asset_id": self.asset_id,
            "location": {
                "latitude": self.location.latitude,
                "longitude": self.location.longitude,
            },
            "occurred_at": self.occurred_at.isoformat(),
            "severity": self.severity.value,
            "status": self.status.value,
            "observations": [
                {
                    "observation_id": item.observation_id,
                    "observation_type": item.observation_type.value,
                    "value": item.value,
                    "source": item.source,
                    "confidence": item.confidence,
                    "observed_at": item.observed_at.isoformat()
                    if item.observed_at
                    else None,
                    "metadata": item.metadata,
                }
                for item in self.observations
            ],
            "evidence": [
                {
                    "evidence_id": item.evidence_id,
                    "title": item.title,
                    "content": item.content,
                    "source_uri": item.source_uri,
                    "source_page": item.source_page,
                    "relevance_score": item.relevance_score,
                }
                for item in self.evidence
            ],
            "hypotheses": [
                {
                    "cause": item.cause,
                    "status": item.status.value,
                    "confidence": item.confidence,
                    "supporting_evidence_ids": list(item.supporting_evidence_ids),
                    "contradicting_evidence_ids": list(item.contradicting_evidence_ids),
                    "rationale": item.rationale,
                }
                for item in self.hypotheses
            ],
        }

