"""Provider-independent image and audio observation interfaces."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .domain import Observation, ObservationType


class VisionProvider:
    def analyze(self, image_path: str | Path, *, incident_id: str) -> tuple[Observation, ...]:
        raise NotImplementedError


class HuggingFaceVisionProvider(VisionProvider):
    """Optional local image-captioning provider backed by Transformers."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv(
            "GRIDPULSE_VISION_MODEL", "Salesforce/blip-image-captioning-base"
        )
        self._pipeline = None

    def analyze(self, image_path: str | Path, *, incident_id: str) -> tuple[Observation, ...]:
        try:
            from transformers import pipeline
        except ImportError as error:
            raise RuntimeError(
                "Local vision dependencies are not installed. Install the vision extra "
                "or disable GRIDPULSE_USE_LOCAL_VISION."
            ) from error
        if self._pipeline is None:
            self._pipeline = _load_vision_pipeline(self.model_name)
        result = self._pipeline(str(image_path), max_new_tokens=50)
        caption = str(result[0].get("generated_text", "")).strip() if result else ""
        if not caption:
            raise RuntimeError("Local vision model returned an empty caption")
        return (
            Observation(
                observation_id=f"{incident_id}:vision:1",
                observation_type=ObservationType.VISUAL,
                value=f"Image caption: {caption}",
                source=str(image_path),
                confidence=0.7,
            ),
        )


def build_vision_provider() -> VisionProvider:
    """Select local image analysis only when explicitly enabled."""

    if os.getenv("GRIDPULSE_USE_LOCAL_VISION", "false").lower() in {"1", "true", "yes"}:
        return HuggingFaceVisionProvider()
    return DemoVisionProvider()


class SpeechProvider:
    def transcribe(self, audio_path: str | Path, *, incident_id: str) -> str:
        raise NotImplementedError


class WhisperSpeechProvider(SpeechProvider):
    """Optional local Whisper transcription provider.

    The model is imported and loaded lazily so the default demo remains
    dependency-free. Set ``GRIDPULSE_USE_LOCAL_WHISPER=true`` to opt in.
    """

    def __init__(self, model_size: str | None = None) -> None:
        self.model_size = model_size or os.getenv("GRIDPULSE_WHISPER_MODEL", "base")
        self._model = None

    def transcribe(self, audio_path: str | Path, *, incident_id: str) -> str:
        try:
            import whisper
        except ImportError as error:
            raise RuntimeError(
                "Local Whisper is not installed. Install the audio extra or disable "
                "GRIDPULSE_USE_LOCAL_WHISPER."
            ) from error
        if self._model is None:
            self._model = _load_whisper_model(self.model_size)
        prompt = os.getenv(
            "GRIDPULSE_WHISPER_PROMPT",
            "Utility field note. Asset ID POLE-900. Pole, crossarm, transformer, conductor, "
            "substation, access road, and qualified crew.",
        )
        result = self._model.transcribe(
            str(audio_path), fp16=False, language="en", initial_prompt=prompt
        )
        transcript = str(result.get("text", "")).strip()
        if not transcript:
            raise RuntimeError("Whisper returned an empty transcript")
        return transcript


@lru_cache(maxsize=3)
def _load_whisper_model(model_size: str):
    import whisper

    return whisper.load_model(model_size)


@lru_cache(maxsize=2)
def _load_vision_pipeline(model_name: str):
    from transformers import pipeline

    return pipeline("image-to-text", model=model_name)


def build_speech_provider() -> SpeechProvider:
    """Select local Whisper only when explicitly enabled; otherwise use fallback."""

    if os.getenv("GRIDPULSE_USE_LOCAL_WHISPER", "false").lower() in {"1", "true", "yes"}:
        return WhisperSpeechProvider()
    return DemoSpeechProvider()


@dataclass(frozen=True, slots=True)
class DemoVisionProvider(VisionProvider):
    """Deterministic fallback for the portfolio demo without model credentials.

    Real VLM and object-detection providers can implement the same interface.
    The fallback deliberately labels its observations as synthetic rather than
    pretending to inspect an image it cannot access.
    """

    def analyze(self, image_path: str | Path, *, incident_id: str) -> tuple[Observation, ...]:
        filename = Path(image_path).name.lower()
        if "storm" in filename or "pole" in filename:
            value = "Synthetic demo observation: upper crossarm appears fractured; transformer appears intact."
            confidence = 0.86
        elif "tree" in filename or "vegetation" in filename:
            value = "Synthetic demo observation: vegetation appears to contact an overhead conductor."
            confidence = 0.82
        else:
            value = "Synthetic demo observation: no configured visual fixture was found."
            confidence = 0.2
        return (
            Observation(
                observation_id=f"{incident_id}:vision:1",
                observation_type=ObservationType.VISUAL,
                value=value,
                source=str(image_path),
                confidence=confidence,
            ),
        )


@dataclass(frozen=True, slots=True)
class DemoSpeechProvider(SpeechProvider):
    """Reads a sidecar transcript or returns a clearly labelled demo note."""

    def transcribe(self, audio_path: str | Path, *, incident_id: str) -> str:
        path = Path(audio_path)
        sidecar = path.with_suffix(".txt")
        if sidecar.exists():
            return sidecar.read_text(encoding="utf-8").strip()
        if "storm" in path.name.lower() or "pole" in path.name.lower():
            return "Synthetic demo note: pole is leaning toward the road and the upper crossarm is broken."
        return "Synthetic demo note: no configured transcript was found."


class MediaProcessor:
    def __init__(
        self,
        vision: VisionProvider | None = None,
        speech: SpeechProvider | None = None,
    ) -> None:
        self.vision = vision or build_vision_provider()
        self.speech = speech or build_speech_provider()

    def observations_from_image(self, image_path: str | Path, *, incident_id: str) -> tuple[Observation, ...]:
        return self.vision.analyze(image_path, incident_id=incident_id)

    def observation_from_audio(self, audio_path: str | Path, *, incident_id: str) -> Observation:
        return Observation(
            observation_id=f"{incident_id}:audio:1",
            observation_type=ObservationType.AUDIO,
            value=self.speech.transcribe(audio_path, incident_id=incident_id),
            source=str(audio_path),
            confidence=0.8,
        )
