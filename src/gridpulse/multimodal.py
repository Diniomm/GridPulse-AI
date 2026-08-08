"""Provider-independent image and audio observation interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .domain import Observation, ObservationType


class VisionProvider:
    def analyze(self, image_path: str | Path, *, incident_id: str) -> tuple[Observation, ...]:
        raise NotImplementedError


class SpeechProvider:
    def transcribe(self, audio_path: str | Path, *, incident_id: str) -> str:
        raise NotImplementedError


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
        self.vision = vision or DemoVisionProvider()
        self.speech = speech or DemoSpeechProvider()

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

