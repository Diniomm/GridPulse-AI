"""Streamlit entrypoint for the zero-cost GridPulse demo.

Run from the repository root with:

    streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gridpulse.demo import build_demo_workflow, demo_incident_options  # noqa: E402


def main() -> None:
    try:
        import streamlit as st
    except ImportError as error:  # pragma: no cover - exercised by Streamlit runtime
        raise SystemExit(
            "Streamlit is not installed. Install the app extra with: "
            "pip install -e '.[app]'"
        ) from error

    st.set_page_config(page_title="GridPulse AI", page_icon="⚡", layout="wide")
    st.title("⚡ GridPulse AI")
    st.caption("Multimodal infrastructure-incident triage — demo decision support")

    with st.sidebar:
        st.header("Incident input")
        options = demo_incident_options()
        incident_id = st.selectbox("Demo incident", list(options))
        incident = options[incident_id]
        image = st.file_uploader("Optional field photograph", type=["png", "jpg", "jpeg"])
        audio = st.file_uploader("Optional technician voice note", type=["wav", "mp3", "m4a"])
        run = st.button("Run investigation", type="primary", use_container_width=True)
        st.divider()
        st.info(
            "This demo uses synthetic incident data and public-style fixtures. "
            "It never controls infrastructure and requires human approval."
        )

    if image is not None:
        st.image(image, caption="Uploaded field photograph", use_container_width=True)

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Incident")
        st.write(f"**{incident.title}**")
        st.write(incident.description)
        st.metric("Severity", incident.severity.value.upper())
        st.map(
            [{"lat": incident.location.latitude, "lon": incident.location.longitude}],
            zoom=10,
        )

    if run:
        workflow = build_demo_workflow()
        result = workflow.run(
            incident,
            image_path=image.name if image is not None else "storm-pole.jpg",
            audio_path=audio.name if audio is not None else "storm-pole.wav",
        )
        st.session_state["last_result"] = result

    result = st.session_state.get("last_result")
    with right:
        st.subheader("Investigation status")
        if result is None:
            st.info("Choose an incident and click Run investigation.")
        else:
            report = result.state.report
            if result.state.status == "awaiting_review":
                st.warning("Awaiting human approval")
            elif result.state.status == "approved":
                st.success("Report approved by human reviewer")
            elif result.state.status == "rejected":
                st.error("Report rejected by human reviewer")
            st.write(report.get("recommendation"))
            if result.state.errors:
                st.error("; ".join(result.state.errors))

            if result.state.status == "awaiting_review":
                approval_col, rejection_col = st.columns(2)
                with approval_col:
                    if st.button("Approve report", use_container_width=True):
                        result.approve()
                        st.rerun()
                with rejection_col:
                    rejection_reason = st.text_input("Rejection reason", key="rejection_reason")
                    if st.button("Reject report", use_container_width=True):
                        if rejection_reason.strip():
                            result.reject(rejection_reason)
                            st.rerun()
                        st.error("A rejection reason is required.")

    if result is not None:
        st.divider()
        evidence_col, hypothesis_col = st.columns(2)
        with evidence_col:
            st.subheader("Observations and evidence")
            for observation in result.state.observations:
                st.write(
                    f"**{observation.observation_type.value}** — {observation.value} "
                    f"({observation.confidence:.0%})"
                )
            for evidence in result.state.evidence:
                st.markdown(f"- [{evidence.title}, p. {evidence.source_page or '—'}]({evidence.source_uri})")
        with hypothesis_col:
            st.subheader("Cause hypotheses")
            for hypothesis in result.state.hypotheses:
                st.write(f"**{hypothesis.cause}** — {hypothesis.status.value} ({hypothesis.confidence:.0%})")
                st.caption(hypothesis.rationale)

        with st.expander("Structured report"):
            st.json(result.state.report)


if __name__ == "__main__":
    main()
