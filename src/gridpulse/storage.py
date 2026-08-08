"""Persistence contracts and an in-memory implementation for the MVP."""

from __future__ import annotations

from typing import Protocol

from .domain import Asset, Incident


class IncidentRepository(Protocol):
    def save_asset(self, asset: Asset) -> Asset: ...

    def get_asset(self, asset_id: str) -> Asset | None: ...

    def save_incident(self, incident: Incident) -> Incident: ...

    def get_incident(self, incident_id: str) -> Incident | None: ...

    def list_incidents(self) -> tuple[Incident, ...]: ...


class InMemoryIncidentRepository:
    """Small deterministic repository used before the database is introduced."""

    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}
        self._incidents: dict[str, Incident] = {}

    def save_asset(self, asset: Asset) -> Asset:
        self._assets[asset.asset_id] = asset
        return asset

    def get_asset(self, asset_id: str) -> Asset | None:
        return self._assets.get(asset_id)

    def save_incident(self, incident: Incident) -> Incident:
        self._incidents[incident.incident_id] = incident
        return incident

    def get_incident(self, incident_id: str) -> Incident | None:
        return self._incidents.get(incident_id)

    def list_incidents(self) -> tuple[Incident, ...]:
        return tuple(self._incidents.values())

