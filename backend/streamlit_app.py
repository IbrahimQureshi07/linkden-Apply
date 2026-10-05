"""Minimal UI for Stage 1 personal testing."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.db.database import SessionLocal, init_db
from app.models.schemas import CandidateProfile, Stage1RunRequest
from app.pipelines.stage1_run import run_stage1_pipeline_sync


def _render_profile(profile: CandidateProfile) -> None:
    name = profile.full_name or "—"
    st.markdown(f"### {name}")
    if profile.headline:
        st.markdown(f"**{profile.headline}**")
    if profile.summary:
        st.write(profile.summary)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Seniority**")
        st.write(profile.seniority or "—")
        st.markdown("**Years of experience**")
        st.write(profile.years_experience if profile.years_experience is not None else "—")
    with c2:
        st.markdown("**Target job titles**")
        st.write(", ".join(profile.job_titles) if profile.job_titles else "—")
        st.markdown("**Industries**")
        st.write(", ".join(profile.industries) if profile.industries else "—")

    st.markdown("**Skills**")
    st.write(", ".join(profile.skills) if profile.skills else "—")

    if profile.keywords:
        st.markdown("**Keywords**")
        st.write(", ".join(profile.keywords))

    if profile.languages:
        st.markdown("**Languages**")
        st.write(", ".join(profile.languages))

    if profile.location_preferences:
        st.markdown("**Location preferences**")
        st.write(", ".join(profile.location_preferences))


st.set_page_config(page_title="Stage 1 — CV to Jobs", layout="wide")
st.title("Stage 1: CV → Jobs → Google Sheet")
st.caption("Personal MVP — Pakistan default, JSearch + OpenAI")

uploaded = st.file_uploader("Upload CV (PDF or DOCX)", type=["pdf", "docx"])
loc_text = st.text_input(
    "Locations (comma-separated)",
    "Karachi",
    help=(
        "Strict export filter: Karachi → only Karachi; "
        "Karachi, Lahore → those cities only; "
        "Pakistan → all Pakistan; "
        "add Remote to also include remote roles."
    ),
)
st.caption(
    "Location is **strict on export**: whatever you type here is what should appear in the sheet."
)

min_score = st.slider(
    "Min match score (quality gate 0–100 — NOT number of jobs)",
    min_value=0,
    max_value=100,
    value=70,
    help=(
        "Each job gets an AI fit score 0–100. "
        "Setting 70 exports only jobs scored 70+. "
        "This is NOT 'export 70 jobs'."
    ),
)
st.caption(
    "Example: **70** = stronger matches only. **0** = export almost everything (more weak jobs)."
)

if st.button("Run Stage 1", type="primary", disabled=not uploaded):
    init_db()
    locations = [x.strip() for x in loc_text.split(",") if x.strip()]
    options = Stage1RunRequest(locations=locations, min_match_score=min_score)
    db = SessionLocal()
    try:
        with st.spinner("Running pipeline (CV parse → jobs → match → sheet)…"):
            result = run_stage1_pipeline_sync(
                uploaded.getvalue(),
                uploaded.name,
                db,
                options,
            )
        st.success(result.message)
        col1, col2 = st.columns(2)
        col1.metric("Jobs found (deduped)", result.jobs_found)
        col2.metric("New jobs exported", result.jobs_exported)
        if result.sheet_url:
            st.link_button("Open Google Sheet", result.sheet_url)
        with st.expander("Profile extracted", expanded=True):
            _render_profile(result.profile)
    except Exception as exc:
        st.error(str(exc))
    finally:
        db.close()
