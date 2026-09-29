"""Minimal UI for Stage 1 personal testing."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.db.database import SessionLocal, init_db
from app.models.schemas import Stage1RunRequest
from app.pipelines.stage1_run import run_stage1_pipeline_sync

st.set_page_config(page_title="Stage 1 — CV to Jobs", layout="wide")
st.title("Stage 1: CV → Jobs → Google Sheet")
st.caption("Personal MVP — Pakistan default, JSearch + OpenAI")

uploaded = st.file_uploader("Upload CV (PDF or DOCX)", type=["pdf", "docx"])
loc_text = st.text_input(
    "Locations (comma-separated)",
    "Pakistan, Karachi, Lahore, Remote",
)
min_score = st.slider("Minimum match score to export", 0, 100, 0)

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
        col1, col2, col3 = st.columns(3)
        col1.metric("Jobs found (deduped)", result.jobs_found)
        col2.metric("Jobs exported", result.jobs_exported)
        col3.metric("Run ID", result.run_id[:8])
        if result.sheet_url:
            st.link_button("Open Google Sheet", result.sheet_url)
        with st.expander("Profile extracted"):
            st.json(json.loads(result.profile.model_dump_json()))
    except Exception as exc:
        st.error(str(exc))
    finally:
        db.close()
