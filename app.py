"""Streamlit entrypoint for the zero-cost GridPulse demo."""

from __future__ import annotations

import os
import re
import sys
import tempfile
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gridpulse.demo import build_demo_workflow, demo_incident_options  # noqa: E402
from gridpulse.exports import report_to_pdf  # noqa: E402
from gridpulse.intake import build_custom_incident  # noqa: E402
from gridpulse.storage import SQLiteIncidentRepository  # noqa: E402


LOCAL_REPOSITORY = SQLiteIncidentRepository(PROJECT_ROOT / "data" / "gridpulse.db")


def _badge(st, label: str, tone: str = "neutral") -> None:
    """Render a compact enterprise-style status pill."""

    st.markdown(
        f'<span class="gp-badge gp-badge-{tone}">{label}</span>',
        unsafe_allow_html=True,
    )


def _safe_filename(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").lower()
    return normalized or "incident"


def _save_upload(
    upload,
    *,
    persist: bool = False,
    incident_id: str | None = None,
    file_prefix: str | None = None,
) -> str | None:
    """Save an upload for provider adapters and optionally retain it for history."""

    if upload is None:
        return None
    suffix = Path(upload.name).suffix or ".bin"
    if persist and incident_id:
        upload_dir = PROJECT_ROOT / "data" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        prefix = _safe_filename(file_prefix or incident_id)
        destination = upload_dir / f"{prefix}-{uuid.uuid4().hex[:8]}{suffix}"
        destination.write_bytes(upload.getvalue())
        return str(destination)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="gridpulse-") as handle:
        handle.write(upload.getvalue())
        return handle.name


def _report_snapshot(
    result,
    *,
    image_path: str | None = None,
    audio_path: str | None = None,
) -> dict[str, object]:
    """Add the rendered investigation sections to the persisted report payload."""

    snapshot = dict(result.state.report)
    snapshot["observations"] = [
        {
            "type": observation.observation_type.value,
            "value": observation.value,
            "confidence": observation.confidence,
            "source": observation.source,
        }
        for observation in result.state.observations
    ]
    snapshot["evidence"] = [
        {
            "title": evidence.title,
            "source_uri": evidence.source_uri,
            "source_page": evidence.source_page,
            "relevance_score": evidence.relevance_score,
        }
        for evidence in result.state.evidence
    ]
    snapshot["hypotheses"] = [
        {
            "cause": hypothesis.cause,
            "status": hypothesis.status.value,
            "confidence": hypothesis.confidence,
            "rationale": hypothesis.rationale,
        }
        for hypothesis in result.state.hypotheses
    ]
    snapshot["image_path"] = image_path
    snapshot["audio_path"] = audio_path
    return snapshot


def _open_saved_report_dialog(st, saved_report) -> None:
    """Display a persisted report in a full review dialog."""

    @st.dialog("Saved incident report", width="large")
    def show_report() -> None:
        report = saved_report.report
        st.caption(
            f"{saved_report.incident_title} | Incident {saved_report.incident_id} | "
            f"Saved {saved_report.updated_at}"
        )
        _badge(st, saved_report.status, "success" if saved_report.status == "approved" else "warning")
        st.subheader("Recommendation")
        st.write(report.get("recommendation", "No recommendation recorded."))

        image_path = report.get("image_path")
        if image_path and Path(str(image_path)).exists():
            st.image(str(image_path), caption="Saved field photograph", use_container_width=True)

        _download_report_buttons(
            st,
            report,
            title=saved_report.incident_title,
            image_path=str(image_path) if image_path else None,
            key_prefix=f"saved-{saved_report.incident_id}",
        )

        observations, evidence = st.columns(2)
        with observations:
            st.markdown("#### Observations")
            for observation in report.get("observations", []):
                with st.container(border=True):
                    st.markdown(f"**{str(observation.get('type', 'Observation')).title()}**")
                    st.write(observation.get("value", ""))
                    st.caption(
                        f"Confidence: {float(observation.get('confidence', 0)):.0%} | "
                        f"Source: {Path(str(observation.get('source', ''))).name}"
                    )
        with evidence:
            st.markdown("#### Evidence and citations")
            for item in report.get("evidence", []):
                with st.container(border=True):
                    page = f" | Page {item.get('source_page')}" if item.get("source_page") else ""
                    st.markdown(f"**{item.get('title', 'Evidence')}{page}**")
                    st.caption(str(item.get("source_uri", "")))

        st.markdown("#### Cause hypotheses")
        for hypothesis in report.get("hypotheses", []):
            with st.container(border=True):
                st.markdown(
                    f"**{hypothesis.get('cause', 'Unresolved')}** - "
                    f"{hypothesis.get('status', 'unknown')} "
                    f"({float(hypothesis.get('confidence', 0)):.0%})"
                )
                st.write(hypothesis.get("rationale", ""))
        if saved_report.reviewer_reason:
            st.markdown("#### Reviewer reason")
            st.write(saved_report.reviewer_reason)
        with st.expander("Full structured report"):
            st.json(report)

    show_report()


def _download_report_buttons(
    st,
    report: dict[str, object],
    *,
    title: str,
    image_path: str | None,
    key_prefix: str,
) -> None:
    """Render the PDF download control."""

    st.markdown("#### Download report")
    try:
        pdf = report_to_pdf(report, title=title, image_path=image_path)
    except RuntimeError as error:
        st.caption(str(error))
    else:
        st.download_button(
            "Download PDF",
            data=pdf,
            file_name=f"{_safe_filename(title)}.pdf",
            mime="application/pdf",
            key=f"{key_prefix}-pdf",
            use_container_width=True,
        )


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
        with st.expander("Saved report history"):
            saved_reports = LOCAL_REPOSITORY.list_reports()
            if not saved_reports:
                st.caption("No saved reports yet.")
            else:
                selected_report_id = st.selectbox(
                    "View saved report",
                    [saved.incident_id for saved in saved_reports[:10]],
                    format_func=lambda report_id: next(
                        saved.incident_title
                        for saved in saved_reports
                        if saved.incident_id == report_id
                    ),
                    key="saved_report_selector",
                )
                selected_report = next(
                    saved for saved in saved_reports if saved.incident_id == selected_report_id
                )
                st.write(f"**Status:** {selected_report.status}")
                st.caption(f"Saved: {selected_report.updated_at}")
                if st.button("Open full report", key="open_saved_report"):
                    st.session_state["saved_report_to_view"] = selected_report_id
                confirm_delete = st.checkbox(
                    "Confirm permanent deletion",
                    key="confirm_saved_report_delete",
                )
                if st.button("Delete saved report", disabled=not confirm_delete):
                    for key in ("image_path", "audio_path"):
                        saved_path = selected_report.report.get(key)
                        if saved_path:
                            Path(str(saved_path)).unlink(missing_ok=True)
                    LOCAL_REPOSITORY.delete_report(selected_report.incident_id)
                    st.session_state.pop("last_persisted_report", None)
                    st.rerun()

    report_to_view = st.session_state.pop("saved_report_to_view", None)
    if report_to_view:
        saved_report = next(
            (item for item in LOCAL_REPOSITORY.list_reports() if item.incident_id == report_to_view),
            None,
        )
        if saved_report:
            _open_saved_report_dialog(st, saved_report)

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
        LOCAL_REPOSITORY.save_incident(incident)
        if audio is not None:
            audio_path = _save_upload(
                audio,
                persist=True,
                incident_id=incident.incident_id,
                file_prefix=incident.title,
            )
        elif os.getenv("GRIDPULSE_USE_LOCAL_WHISPER", "false").lower() in {"1", "true", "yes"}:
            audio_path = None
        else:
            audio_path = "storm-pole.wav"
        if image is not None:
            image_path = _save_upload(
                image,
                persist=True,
                incident_id=incident.incident_id,
                file_prefix=incident.title,
            )
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
        stored_report = _report_snapshot(
            result,
            image_path=image_path if image is not None else None,
            audio_path=audio_path if audio is not None else None,
        )
        st.session_state["last_persisted_report"] = stored_report
        LOCAL_REPOSITORY.save_report(
            incident.incident_id,
            incident_title=incident.title,
            status=result.state.status,
            report=stored_report,
        )

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
                            stored_report = dict(
                                st.session_state.get("last_persisted_report", result.state.report)
                            )
                            stored_report.update(result.state.report)
                            LOCAL_REPOSITORY.save_report(
                                result.state.incident.incident_id,
                                incident_title=result.state.incident.title,
                                status=result.state.status,
                                report=stored_report,
                            )
                            st.rerun()
                    with rejection_col:
                        rejection_reason = st.text_input("Rejection reason", key="rejection_reason")
                        if st.button("Reject report", use_container_width=True):
                            if rejection_reason.strip():
                                result.reject(rejection_reason)
                                stored_report = dict(
                                    st.session_state.get("last_persisted_report", result.state.report)
                                )
                                stored_report.update(result.state.report)
                                LOCAL_REPOSITORY.save_report(
                                    result.state.incident.incident_id,
                                    incident_title=result.state.incident.title,
                                    status=result.state.status,
                                    report=stored_report,
                                    reviewer_reason=rejection_reason,
                                )
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
        live_report = st.session_state.get("last_persisted_report", result.state.report)
        _download_report_buttons(
            st,
            live_report,
            title=incident.title,
            image_path=str(live_report.get("image_path")) if live_report.get("image_path") else None,
            key_prefix=f"live-{incident.incident_id}",
        )

    st.markdown(
        '<div class="gp-footer">Demo decision support only | Uses synthetic incident data and public-style fixtures | Never controls infrastructure | Human approval required</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
