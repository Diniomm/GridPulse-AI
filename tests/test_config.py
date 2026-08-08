import os
import unittest
from unittest.mock import patch

from gridpulse.config import Settings


class SettingsTest(unittest.TestCase):
    def test_safe_defaults_enable_demo_mode(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_env()
        self.assertTrue(settings.demo_mode)
        self.assertEqual(settings.database_url, "sqlite:///./gridpulse.db")

    def test_environment_overrides_are_loaded(self) -> None:
        values = {
            "GRIDPULSE_DEMO_MODE": "false",
            "DATABASE_URL": "postgresql://example",
            "LANGSMITH_TRACING": "yes",
        }
        with patch.dict(os.environ, values, clear=True):
            settings = Settings.from_env()
        self.assertFalse(settings.demo_mode)
        self.assertTrue(settings.langsmith_tracing)
        self.assertEqual(settings.database_url, "postgresql://example")

