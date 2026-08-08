import os
import unittest
from unittest.mock import patch

from gridpulse.multimodal import DemoSpeechProvider, WhisperSpeechProvider, build_speech_provider


class MultimodalProviderTest(unittest.TestCase):
    def test_demo_speech_is_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(build_speech_provider(), DemoSpeechProvider)

    def test_whisper_is_opt_in(self) -> None:
        with patch.dict(os.environ, {"GRIDPULSE_USE_LOCAL_WHISPER": "true"}, clear=True):
            provider = build_speech_provider()
        self.assertIsInstance(provider, WhisperSpeechProvider)

    def test_whisper_reports_missing_optional_dependency(self) -> None:
        provider = WhisperSpeechProvider(model_size="tiny")
        with patch.dict("sys.modules", {"whisper": None}):
            with self.assertRaises(RuntimeError) as context:
                provider.transcribe("missing.wav", incident_id="INC-1")
        self.assertIn("not installed", str(context.exception))
