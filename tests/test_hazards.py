import unittest
from datetime import datetime, timezone

from gridpulse.domain import Coordinates, Incident
from gridpulse.hazards import (
    HazardType,
    NWSClient,
    USGSClient,
    correlate_incident,
    haversine_km,
    parse_nws_alerts,
    parse_usgs_events,
)


class FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.last_url = None
        self.last_headers = None

    def get(self, url, headers=None):
        self.last_url = url
        self.last_headers = headers
        return self.payload


class HazardParsingTest(unittest.TestCase):
    def test_nws_parser_extracts_alert_and_centroid(self) -> None:
        payload = {
            "features": [
                {
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-94.6, 39.1], [-94.5, 39.1], [-94.5, 39.2]]],
                    },
                    "properties": {
                        "id": "https://api.weather.gov/alerts/123",
                        "event": "Severe Thunderstorm Warning",
                        "headline": "Severe Thunderstorm Warning issued",
                        "onset": "2026-08-07T14:00:00Z",
                        "expires": "2026-08-07T16:00:00Z",
                        "severity": "Severe",
                    },
                }
            ]
        }
        events = parse_nws_alerts(payload)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].hazard_type, HazardType.WEATHER_ALERT)
        self.assertAlmostEqual(events[0].location.latitude, 39.1333, places=3)

    def test_usgs_parser_converts_epoch_and_coordinates(self) -> None:
        payload = {
            "features": [
                {
                    "id": "us7000demo",
                    "geometry": {"coordinates": [-94.58, 39.10, 10.0]},
                    "properties": {
                        "title": "M 4.2 - 5 km SE of Kansas City",
                        "time": 1786113000000,
                        "mag": 4.2,
                        "url": "https://earthquake.usgs.gov/example",
                    },
                }
            ]
        }
        events = parse_usgs_events(payload)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].hazard_type, HazardType.EARTHQUAKE)
        self.assertEqual(events[0].location, Coordinates(39.10, -94.58))
        self.assertIsNotNone(events[0].starts_at)

    def test_clients_build_expected_public_urls(self) -> None:
        nws_transport = FakeTransport({"features": []})
        NWSClient(nws_transport).active_for_point(Coordinates(39.1, -94.5))
        self.assertIn("/alerts/active?point=39.1,-94.5", nws_transport.last_url)

        usgs_transport = FakeTransport({"features": []})
        USGSClient(usgs_transport).recent_events()
        self.assertIn("all_day.geojson", usgs_transport.last_url)


class CorrelationTest(unittest.TestCase):
    def test_haversine_is_zero_for_same_point(self) -> None:
        point = Coordinates(39.1, -94.5)
        self.assertAlmostEqual(haversine_km(point, point), 0.0)

    def test_correlator_filters_by_distance_and_time(self) -> None:
        incident = Incident(
            incident_id="INC-1",
            title="Test outage",
            description="Synthetic outage",
            asset_id="POLE-1",
            location=Coordinates(39.1, -94.5),
            occurred_at=datetime(2026, 8, 7, 15, 0, tzinfo=timezone.utc),
        )
        nearby = parse_usgs_events(
            {
                "features": [
                    {
                        "id": "nearby",
                        "geometry": {"coordinates": [-94.51, 39.11, 5]},
                        "properties": {"title": "Nearby quake", "time": 1786114800000},
                    },
                    {
                        "id": "far-away",
                        "geometry": {"coordinates": [-100.0, 40.0, 5]},
                        "properties": {"title": "Far quake", "time": 1786114800000},
                    },
                ]
            }
        )
        matches = correlate_incident(incident, nearby, radius_km=10, max_temporal_distance_hours=2)
        self.assertEqual([match.event.event_id for match in matches], ["nearby"])

