"""Streamlit entrypoint for the zero-cost GridPulse demo."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gridpulse.demo import build_demo_workflow, demo_incident_options  # noqa: E402
from gridpulse.intake import build_custom_incident  # noqa: E402


def _badge(st, label: str, tone: str = "neutral") -> None:
    """Render a compact enterprise-style status pill."""

    st.markdown(
        f'<span class="gp-badge gp-badge-{tone}">{label}</span>',
        unsafe_allow_html=True,
    )


def _save_upload(upload) -> str | None:
    """Save a Streamlit upload to a temporary path for provider adapters."""

    if upload is None:
        return None
    suffix = Path(upload.name).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="gridpulse-") as handle:
        handle.write(upload.getvalue())
        return handle.name


def _evidence_markup(evidence) -> str:
    """Render a citation link only when its source can open in a browser."""

    page = f", p. {evidence.source_page}" if evidence.source_page else ""
    label = f"{evidence.title}{page}"
    source = evidence.source_uri
    if source.startswith(("http://", "https://")):
        return f"- [{label}]({source})"
    return f"- {label} — `{source}`"


def main() -> None:
    try:
        import streamlit as st
    except ImportError as error:  # pragma: no cover - exercised by Streamlit runtime
        raise SystemExit(
            "Streamlit is not installed. Install the app extra with: "
            "pip install -e '.[app]'"
        ) from error

    st.set_page_config(page_title="GridPulse AI", page_icon="G", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2.2rem; padding-bottom: 1rem; max-width: 1440px; }
        /* Keep Streamlit's header, theme controls, and sidebar toggle available. */
        [data-testid="stDeployButton"], [data-testid="stDeployButton"] button,
        button[title="Deploy"], button[aria-label="Deploy"] { display: none !important; }
        h1, h2, h3, h4 { letter-spacing: -0.02em; }
        h1 { font-size: 2.35rem !important; margin-bottom: 0.15rem !important; }
        h3 { margin-bottom: 0.25rem !important; }
        [data-testid="stSidebar"] { border-right: 1px solid rgba(128, 128, 128, 0.18); }
        [data-testid="stMetric"] { background: rgba(128, 128, 128, 0.06); border-radius: 0.7rem; padding: 0.65rem 0.85rem; }
        div.stButton > button[kind="primary"], div.stButton > button[data-testid="stBaseButton-primary"] { background: #2563eb !important; border-color: #2563eb !important; color: #ffffff !important; }
        div.stButton > button[kind="primary"]:hover, div.stButton > button[data-testid="stBaseButton-primary"]:hover { background: #1d4ed8 !important; border-color: #1d4ed8 !important; }
        .gp-eyebrow { color: #6b7280; font-size: 0.76rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.25rem; }
        .gp-subtitle { color: #6b7280; font-size: 1rem; margin-bottom: 1.4rem; }
        .gp-badge { border-radius: 999px; display: inline-block; font-size: 0.72rem; font-weight: 750; letter-spacing: 0.04em; padding: 0.28rem 0.68rem; text-transform: uppercase; }
        .gp-badge-neutral { background: rgba(107, 114, 128, 0.14); color: #4b5563; }
        .gp-badge-warning { background: rgba(245, 158, 11, 0.16); color: #b45309; }
        .gp-badge-success { background: #16a34a; color: #ffffff; }
        .gp-badge-danger { background: #dc2626; color: #ffffff; }
        .gp-footer { border-top: 1px solid rgba(128, 128, 128, 0.18); color: #6b7280; font-size: 0.74rem; margin-top: 2rem; padding-top: 0.9rem; }
        [data-testid="stHorizontalBlock"]:has(.gp-top-card) [data-testid="stVerticalBlockBorderWrapper"] { min-height: 230px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("GridPulse AI")
    st.markdown(
        '<div class="gp-subtitle">Multimodal infrastructure-incident triage for faster, evidence-backed decisions.</div>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Incident input")
        options = demo_incident_options()
        input_mode = st.radio("Input mode", ["Demo incident", "Custom incident"])
        incident = None
        if input_mode == "Demo incident":
            incident_id = st.selectbox("Demo incident", list(options))
            incident = options[incident_id]
            image = st.file_uploader("Optional field photograph", type=["png", "jpg", "jpeg"])
            audio = st.file_uploader("Optional technician voice note", type=["wav", "mp3", "m4a"])
            run = st.button("Run investigation", type="primary", use_container_width=True)
        else:
            incident = st.session_state.get("custom_incident")
            with st.form("custom_incident_form"):
                custom_title = st.text_input("Incident title")
                custom_description = st.text_area("What happened?", height=100)
                custom_asset = st.text_input("Asset ID", placeholder="POLE-900")
                custom_latitude = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=39.0997, format="%.4f")
                custom_longitude = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-94.5786, format="%.4f")
                custom_severity = st.selectbox("Severity", ["low", "medium", "high", "critical"], index=1)
                image = st.file_uploader("Optional field photograph", type=["png", "jpg", "jpeg"])
                audio = st.file_uploader("Optional technician voice note", type=["wav", "mp3", "m4a"])
                run = st.form_submit_button("Run investigation", type="primary", use_container_width=True)
            if run:
                try:
                    incident = build_custom_incident(
                        title=custom_title,
                        description=custom_description,
                        asset_id=custom_asset,
                        latitude=custom_latitude,
                        longitude=custom_longitude,
                        severity=custom_severity,
                    )
                    st.session_state["custom_incident"] = incident
                except ValueError as error:
                    st.error(str(error))
            elif not (custom_title.strip() and custom_description.strip() and custom_asset.strip()):
                st.caption("Complete the fields above, then submit the form to continue.")

    if incident is None:
        st.info("Complete the custom incident fields in the sidebar to view the investigation workspace.")
        return

    if image is not None:
        st.image(image, caption="Uploaded field photograph", use_container_width=True)

    left, right = st.columns([1, 1])
    with left:
        with st.container(border=True):
            st.markdown('<span class="gp-top-card"></span>', unsafe_allow_html=True)
            st.markdown("#### Incident overview")
            st.write(f"**{incident.title}**")
            st.write(incident.description)
            severity_tone = "danger" if incident.severity.value in {"high", "critical"} else "warning"
            st.caption("Severity")
            _badge(st, incident.severity.value, severity_tone)

        with st.container(border=True):
            st.markdown("#### Incident location")
            st.caption(
                f"Asset {incident.asset_id} | {incident.location.latitude:.4f}, "
                f"{incident.location.longitude:.4f}"
            )
            st.map(
                [{"lat": incident.location.latitude, "lon": incident.location.longitude}],
                zoom=10,
            )

    loading_slot = right.empty()
    if run:
        workflow = build_demo_workflow()
        if audio is not None:
            audio_path = _save_upload(audio)
        elif os.getenv("GRIDPULSE_USE_LOCAL_WHISPER", "false").lower() in {"1", "true", "yes"}:
            audio_path = None
        else:
            audio_path = "storm-pole.wav"
        if image is not None:
            image_path = _save_upload(image)
        elif os.getenv("GRIDPULSE_USE_LOCAL_VISION", "false").lower() in {"1", "true", "yes"}:
            image_path = None
        else:
            image_path = "storm-pole.jpg"
        with loading_slot.container():
            st.markdown("#### Investigation in progress")
            st.caption("Extracting audio details, analyzing the image, and assembling evidence.")
            progress = st.progress(8, text="Preparing local providers...")
            progress.progress(20, text="Loading local models...")
            result = workflow.run(incident, image_path=image_path, audio_path=audio_path)
            progress.progress(100, text="Investigation complete")
        loading_slot.empty()
        st.session_state["last_result"] = result

    result = st.session_state.get("last_result")
    with right:
        with st.container(border=True):
            st.markdown("#### Investigation status")
            st.markdown('<span class="gp-top-card"></span>', unsafe_allow_html=True)
            if result is None:
                _badge(st, "Ready to run", "neutral")
                st.write("Choose an incident and run the investigation to assemble evidence.")
            else:
                report = result.state.report
                if result.state.status == "awaiting_review":
                    _badge(st, "Awaiting review", "warning")
                elif result.state.status == "approved":
                    _badge(st, "Approved", "success")
                elif result.state.status == "rejected":
                    _badge(st, "Rejected", "danger")
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
            with st.container(border=True):
                st.markdown("#### Observations and evidence")
                for observation in result.state.observations:
                    st.write(
                        f"**{observation.observation_type.value}** - {observation.value} "
                        f"({observation.confidence:.0%})"
                    )
                for evidence in result.state.evidence:
                    st.markdown(_evidence_markup(evidence))
        with hypothesis_col:
            with st.container(border=True):
                st.markdown("#### Cause hypotheses")
                for hypothesis in result.state.hypotheses:
                    st.write(
                        f"**{hypothesis.cause}** - {hypothesis.status.value} "
                        f"({hypothesis.confidence:.0%})"
                    )
                    st.caption(hypothesis.rationale)

        with st.expander("Structured report"):
            st.json(result.state.report)

    st.markdown(
        '<div class="gp-footer">Demo decision support only | Uses synthetic incident data and public-style fixtures | Never controls infrastructure | Human approval required</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
