import os
import unittest
from unittest.mock import patch

from gridpulse.multimodal import (
    DemoSpeechProvider,
    DemoVisionProvider,
    HuggingFaceVisionProvider,
    WhisperSpeechProvider,
    build_speech_provider,
    build_vision_provider,
)


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

    def test_demo_vision_is_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(build_vision_provider(), DemoVisionProvider)

    def test_local_vision_is_opt_in(self) -> None:
        with patch.dict(os.environ, {"GRIDPULSE_USE_LOCAL_VISION": "true"}, clear=True):
            provider = build_vision_provider()
        self.assertIsInstance(provider, HuggingFaceVisionProvider)

    def test_local_vision_reports_missing_optional_dependency(self) -> None:
        provider = HuggingFaceVisionProvider(model_name="test-model")
        with patch.dict("sys.modules", {"transformers": None}):
            with self.assertRaises(RuntimeError) as context:
                provider.analyze("missing.jpg", incident_id="INC-1")
        self.assertIn("not installed", str(context.exception))
