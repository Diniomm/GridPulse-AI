"""Bounded incident-investigation workflow used by the MVP.

The orchestration contract is deliberately independent of LangGraph so it can
be tested with the standard library. A later adapter can map these named nodes
to a persisted LangGraph StateGraph without changing domain objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .domain import Evidence, Hypothesis, HypothesisStatus, Incident, Observation
from .hazards import HazardEvent, HazardMatch, correlate_incident
from .multimodal import MediaProcessor
from .rag import HybridIndex, RetrievedEvidence


HazardLoader = Callable[[Incident], tuple[HazardEvent, ...]]


@dataclass(slots=True)
class InvestigationState:
    incident: Incident
    observations: list[Observation] = field(default_factory=list)
    hazard_matches: list[HazardMatch] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    report: dict[str, object] = field(default_factory=dict)
    status: str = "new"
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class InvestigationResult:
    state: InvestigationState

    @property
    def requires_human_review(self) -> bool:
        return self.state.status == "awaiting_review"

    def approve(self) -> None:
        self.state.status = "approved"
        self.state.report["review_status"] = "approved"

    def reject(self, reason: str) -> None:
        if not reason.strip():
            raise ValueError("rejection reason cannot be empty")
        self.state.status = "rejected"
        self.state.report["review_status"] = "rejected"
        self.state.report["reviewer_reason"] = reason


class InvestigationWorkflow:
    """Explicit, auditable nodes for the incident investigation path."""

    def __init__(
        self,
        rag_index: HybridIndex,
        *,
        media: MediaProcessor | None = None,
        hazard_loader: HazardLoader | None = None,
    ) -> None:
        self.rag_index = rag_index
        self.media = media or MediaProcessor()
        self.hazard_loader = hazard_loader or (lambda _incident: ())

    def run(
        self,
        incident: Incident,
        *,
        image_path: str | None = None,
        audio_path: str | None = None,
    ) -> InvestigationResult:
        state = InvestigationState(incident=incident, observations=list(incident.observations))
        state.status = "investigating"
        self._intake(state)
        self._process_media(state, image_path=image_path, audio_path=audio_path)
        self._correlate_hazards(state)
        self._retrieve_evidence(state)
        self._rank_hypotheses(state)
        self._verify_and_report(state)
        return InvestigationResult(state)

    def _intake(self, state: InvestigationState) -> None:
        if not state.incident.asset_id.strip():
            state.errors.append("Incident has no asset identifier")

    def _process_media(
        self,
        state: InvestigationState,
        *,
        image_path: str | None,
        audio_path: str | None,
    ) -> None:
        try:
            if image_path:
                state.observations.extend(
                    self.media.observations_from_image(image_path, incident_id=state.incident.incident_id)
                )
            if audio_path:
                state.observations.append(
                    self.media.observation_from_audio(audio_path, incident_id=state.incident.incident_id)
                )
        except (OSError, ValueError) as error:
            state.errors.append(f"Media processing failed: {error}")

    def _correlate_hazards(self, state: InvestigationState) -> None:
        try:
            events = self.hazard_loader(state.incident)
            state.hazard_matches.extend(correlate_incident(state.incident, events))
            for match in state.hazard_matches:
                state.evidence.append(
                    Evidence(
                        evidence_id=f"hazard:{match.event.event_id}",
                        title=match.event.title,
                        content=(
                            f"{match.event.source} event {match.event.event_id} was "
                            f"{match.distance_km:.1f} km from the incident."
                        ),
                        source_uri=match.event.source_url or match.event.source,
                        relevance_score=max(0.0, 1.0 - (match.distance_km / 50)),
                    )
                )
        except (ValueError, TypeError) as error:
            state.errors.append(f"Hazard correlation failed: {error}")

    def _retrieve_evidence(self, state: InvestigationState) -> None:
        query = " ".join(
            [state.incident.title, state.incident.description]
            + [observation.value for observation in state.observations]
        )
        for result in self.rag_index.retrieve(query, top_k=4):
            state.evidence.append(_evidence_from_retrieval(result))

    def _rank_hypotheses(self, state: InvestigationState) -> None:
        text = " ".join(
            [state.incident.description]
            + [observation.value for observation in state.observations]
            + [match.event.title for match in state.hazard_matches]
        ).lower()
        evidence_ids = tuple(evidence.evidence_id for evidence in state.evidence)
        if _contains_contradictory_damage_claim(text):
            state.hypotheses.append(
                Hypothesis(
                    cause="conflicting field evidence",
                    status=HypothesisStatus.INSUFFICIENT_EVIDENCE,
                    confidence=0.1,
                    supporting_evidence_ids=evidence_ids,
                    rationale="Conflicting condition reports require human verification before cause ranking.",
                )
            )
        elif ("crossarm" in text or "pole" in text) and "wind" in text:
            state.hypotheses.append(
                Hypothesis(
                    cause="wind-induced pole or crossarm damage",
                    status=HypothesisStatus.PROBABLE,
                    confidence=0.86,
                    supporting_evidence_ids=evidence_ids,
                    rationale="Pole/crossarm observations align with a nearby wind-related hazard.",
                )
            )
        elif "tree" in text or "vegetation" in text:
            state.hypotheses.append(
                Hypothesis(
                    cause="vegetation contact with overhead conductor",
                    status=HypothesisStatus.POSSIBLE,
                    confidence=0.7,
                    supporting_evidence_ids=evidence_ids,
                    rationale="The incident description contains vegetation or tree-contact evidence.",
                )
            )
        elif "earthquake" in text or state.hazard_matches and any(
            match.event.hazard_type.value == "earthquake" for match in state.hazard_matches
        ):
            state.hypotheses.append(
                Hypothesis(
                    cause="seismic disturbance",
                    status=HypothesisStatus.POSSIBLE,
                    confidence=0.65,
                    supporting_evidence_ids=evidence_ids,
                    rationale="A nearby earthquake event is temporally and spatially relevant.",
                )
            )
        else:
            state.hypotheses.append(
                Hypothesis(
                    cause="unresolved infrastructure incident",
                    status=HypothesisStatus.INSUFFICIENT_EVIDENCE,
                    confidence=0.2,
                    supporting_evidence_ids=evidence_ids,
                    rationale="The available observations do not support a reliable cause.",
                )
            )

    def _verify_and_report(self, state: InvestigationState) -> None:
        top = state.hypotheses[0] if state.hypotheses else None
        if top is None or top.status == HypothesisStatus.INSUFFICIENT_EVIDENCE or not state.evidence:
            state.status = "awaiting_review"
            recommendation = "Request additional evidence or a physical inspection."
        else:
            state.status = "awaiting_review"
            recommendation = "Review the cited evidence before dispatch or restoration action."
        state.report = {
            "incident_id": state.incident.incident_id,
            "status": state.status,
            "recommendation": recommendation,
            "hypotheses": [
                {
                    "cause": hypothesis.cause,
                    "status": hypothesis.status.value,
                    "confidence": hypothesis.confidence,
                    "rationale": hypothesis.rationale,
                }
                for hypothesis in state.hypotheses
            ],
            "citations": [evidence.source_uri for evidence in state.evidence],
            "errors": list(state.errors),
            "requires_human_approval": True,
        }


def _evidence_from_retrieval(result: RetrievedEvidence) -> Evidence:
    return Evidence(
        evidence_id=f"rag:{result.chunk.chunk_id}",
        title=result.chunk.title,
        content=result.chunk.text,
        source_uri=result.chunk.source_uri,
        source_page=result.chunk.page,
        relevance_score=result.score,
    )


def _contains_contradictory_damage_claim(text: str) -> bool:
    """Detect a denial of damage alongside a damage claim in untrusted text."""

    denial_terms = ("intact", "undamaged", "no damage", "no visible damage", "undisturbed")
    damage_terms = ("damage", "damaged", "broken", "fractured", "split")
    conflict_markers = (" but ", " however ", "another note claims", "conflicting", "contradict")
    return (
        any(term in text for term in denial_terms)
        and any(term in text for term in damage_terms)
        and any(marker in text for marker in conflict_markers)
    )
