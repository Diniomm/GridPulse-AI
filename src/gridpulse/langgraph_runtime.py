"""Optional LangGraph adapter for the dependency-free workflow contract."""

from __future__ import annotations

from typing import TypedDict

from .domain import Incident
from .workflow import InvestigationResult, InvestigationState, InvestigationWorkflow


class LangGraphState(TypedDict, total=False):
    incident: Incident
    image_path: str | None
    audio_path: str | None
    runtime: InvestigationState
    result: InvestigationResult


def build_langgraph_app(workflow: InvestigationWorkflow):
    """Build a persisted-runtime-compatible graph when LangGraph is installed.

    The import is lazy so local demo mode remains dependency-free. The graph
    nodes delegate to the same tested workflow methods used by the fallback.
    """

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as error:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            "Install the optional AI dependencies to use the LangGraph adapter: "
            "pip install -e '.[ai]'"
        ) from error

    graph = StateGraph(LangGraphState)

    def intake(state: LangGraphState) -> LangGraphState:
        runtime = InvestigationState(incident=state["incident"], observations=[])
        runtime.status = "investigating"
        workflow._intake(runtime)
        return {**state, "runtime": runtime}

    def multimodal(state: LangGraphState) -> LangGraphState:
        runtime = state["runtime"]
        workflow._process_media(
            runtime,
            image_path=state.get("image_path"),
            audio_path=state.get("audio_path"),
        )
        return state

    def hazards(state: LangGraphState) -> LangGraphState:
        workflow._correlate_hazards(state["runtime"])
        return state

    def retrieval(state: LangGraphState) -> LangGraphState:
        workflow._retrieve_evidence(state["runtime"])
        return state

    def hypotheses(state: LangGraphState) -> LangGraphState:
        workflow._rank_hypotheses(state["runtime"])
        return state

    def report(state: LangGraphState) -> LangGraphState:
        runtime = state["runtime"]
        workflow._verify_and_report(runtime)
        return {**state, "result": InvestigationResult(runtime)}

    graph.add_node("intake", intake)
    graph.add_node("multimodal", multimodal)
    graph.add_node("hazards", hazards)
    graph.add_node("retrieval", retrieval)
    graph.add_node("hypotheses", hypotheses)
    graph.add_node("report", report)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "multimodal")
    graph.add_edge("multimodal", "hazards")
    graph.add_edge("hazards", "retrieval")
    graph.add_edge("retrieval", "hypotheses")
    graph.add_edge("hypotheses", "report")
    graph.add_edge("report", END)
    return graph.compile()

