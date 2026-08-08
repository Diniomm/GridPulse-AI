"""Hazard event models, public-feed parsing, and incident correlation."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Protocol
from urllib.request import Request, urlopen

from .domain import Coordinates, Incident


class HazardType(StrEnum):
    WEATHER_ALERT = "weather_alert"
    EARTHQUAKE = "earthquake"


@dataclass(frozen=True, slots=True)
class HazardEvent:
    event_id: str
    hazard_type: HazardType
    title: str
    source: str
    location: Coordinates | None
    starts_at: datetime | None
    ends_at: datetime | None
    severity: str | None = None
    source_url: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id cannot be empty")
        if not self.title.strip():
            raise ValueError("hazard title cannot be empty")
        if not self.source.strip():
            raise ValueError("hazard source cannot be empty")
        if self.starts_at is not None:
            object.__setattr__(self, "starts_at", _as_utc(self.starts_at))
        if self.ends_at is not None:
            object.__setattr__(self, "ends_at", _as_utc(self.ends_at))


@dataclass(frozen=True, slots=True)
class HazardMatch:
    event: HazardEvent
    distance_km: float
    temporal_distance_hours: float


class JsonTransport(Protocol):
    def get(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]: ...


class UrllibJsonTransport:
    """Small standard-library HTTP adapter; replaceable in tests."""

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    def get(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        request = Request(url, headers=headers or {})
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))


class NWSClient:
    """Client for active National Weather Service alerts."""

    base_url = "https://api.weather.gov/alerts/active"

    def __init__(self, transport: JsonTransport | None = None) -> None:
        self.transport = transport or UrllibJsonTransport()

    def active_for_point(self, location: Coordinates) -> tuple[HazardEvent, ...]:
        url = f"{self.base_url}?point={location.latitude},{location.longitude}"
        payload = self.transport.get(
            url,
            headers={
                "Accept": "application/geo+json, application/ld+json",
                "User-Agent": "GridPulse-MVP/0.1 (portfolio demo)",
            },
        )
        return parse_nws_alerts(payload)


class USGSClient:
    """Client for the USGS real-time GeoJSON earthquake feed."""

    feed_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"

    def __init__(self, transport: JsonTransport | None = None) -> None:
        self.transport = transport or UrllibJsonTransport()

    def recent_events(self) -> tuple[HazardEvent, ...]:
        payload = self.transport.get(self.feed_url, headers={"Accept": "application/json"})
        return parse_usgs_events(payload)


def parse_nws_alerts(payload: dict[str, Any]) -> tuple[HazardEvent, ...]:
    events: list[HazardEvent] = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        events.append(
            HazardEvent(
                event_id=str(properties.get("id") or properties.get("event") or "nws-unknown"),
                hazard_type=HazardType.WEATHER_ALERT,
                title=str(properties.get("headline") or properties.get("event") or "Weather alert"),
                source="NWS",
                location=_geometry_centroid(geometry),
                starts_at=_parse_datetime(properties.get("onset") or properties.get("effective")),
                ends_at=_parse_datetime(properties.get("ends") or properties.get("expires")),
                severity=properties.get("severity"),
                source_url=properties.get("@id") or properties.get("id"),
                metadata={
                    "event": properties.get("event"),
                    "area_desc": properties.get("areaDesc"),
                    "description": properties.get("description"),
                },
            )
        )
    return tuple(events)


def parse_usgs_events(payload: dict[str, Any]) -> tuple[HazardEvent, ...]:
    events: list[HazardEvent] = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        location = None
        if len(coordinates) >= 2:
            location = Coordinates(float(coordinates[1]), float(coordinates[0]))
        event_time = properties.get("time")
        starts_at = (
            datetime.fromtimestamp(event_time / 1000, tz=timezone.utc)
            if isinstance(event_time, (int, float))
            else None
        )
        event_id = str(feature.get("id") or properties.get("code") or "usgs-unknown")
        events.append(
            HazardEvent(
                event_id=event_id,
                hazard_type=HazardType.EARTHQUAKE,
                title=str(properties.get("title") or "Earthquake"),
                source="USGS",
                location=location,
                starts_at=starts_at,
                ends_at=starts_at,
                severity=properties.get("alert"),
                source_url=properties.get("url"),
                metadata={
                    "magnitude": properties.get("mag"),
                    "place": properties.get("place"),
                    "felt": properties.get("felt"),
                },
            )
        )
    return tuple(events)


def correlate_incident(
    incident: Incident,
    events: tuple[HazardEvent, ...],
    *,
    radius_km: float = 50.0,
    max_temporal_distance_hours: float = 24.0,
) -> tuple[HazardMatch, ...]:
    """Return nearby, temporally relevant hazards ordered by distance then recency."""

    matches: list[HazardMatch] = []
    for event in events:
        if event.location is None:
            continue
        distance_km = haversine_km(incident.location, event.location)
        temporal_distance_hours = _temporal_distance_hours(incident.occurred_at, event)
        if distance_km <= radius_km and temporal_distance_hours <= max_temporal_distance_hours:
            matches.append(HazardMatch(event, distance_km, temporal_distance_hours))
    return tuple(sorted(matches, key=lambda item: (item.distance_km, item.temporal_distance_hours)))


def haversine_km(first: Coordinates, second: Coordinates) -> float:
    earth_radius_km = 6371.0088
    lat1, lat2 = math.radians(first.latitude), math.radians(second.latitude)
    delta_lat = math.radians(second.latitude - first.latitude)
    delta_lon = math.radians(second.longitude - first.longitude)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * earth_radius_km * math.asin(math.sqrt(value))


def _temporal_distance_hours(occurred_at: datetime, event: HazardEvent) -> float:
    occurred_at = _as_utc(occurred_at)
    if event.starts_at and event.ends_at and event.starts_at <= occurred_at <= event.ends_at:
        return 0.0
    if event.starts_at and occurred_at < event.starts_at:
        return (event.starts_at - occurred_at).total_seconds() / 3600
    if event.ends_at and occurred_at > event.ends_at:
        return (occurred_at - event.ends_at).total_seconds() / 3600
    if event.starts_at:
        return abs((occurred_at - event.starts_at).total_seconds()) / 3600
    return float("inf")


def _geometry_centroid(geometry: dict[str, Any]) -> Coordinates | None:
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return None
    points: list[tuple[float, float]] = []

    def collect(value: Any) -> None:
        if isinstance(value, list) and len(value) >= 2 and all(
            isinstance(item, (int, float)) for item in value[:2]
        ):
            points.append((float(value[0]), float(value[1])))
            return
        if isinstance(value, list):
            for child in value:
                collect(child)

    collect(coordinates)
    if not points:
        return None
    longitude = sum(point[0] for point in points) / len(points)
    latitude = sum(point[1] for point in points) / len(points)
    return Coordinates(latitude, longitude)


def _parse_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return _as_utc(datetime.fromisoformat(normalized))
    except ValueError:
        return None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
