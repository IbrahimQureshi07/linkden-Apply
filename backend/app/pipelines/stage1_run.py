from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import load_yaml_config
from app.db.models import JobRecord, RunRecord
from app.models.schemas import Stage1RunRequest, Stage1RunResult
from app.services.cv_parser import extract_text_from_bytes
from app.services.dedupe import dedupe_jobs
from app.services.job_providers.jsearch import JSearchProvider
from app.services.matcher import match_jobs
from app.services.profile_extractor import extract_profile
from app.services.query_generator import generate_search_queries
from app.services.sheets_exporter import export_jobs_to_sheet


async def run_stage1_pipeline(
    cv_bytes: bytes,
    filename: str,
    db: Session,
    options: Stage1RunRequest | None = None,
) -> Stage1RunResult:
    options = options or Stage1RunRequest()
    yaml_cfg = load_yaml_config()

    run_id = str(uuid.uuid4())
    cv_hash = hashlib.sha256(cv_bytes).hexdigest()

    record = RunRecord(id=run_id, status="running", cv_hash=cv_hash)
    db.add(record)
    db.commit()

    try:
        cv_text = extract_text_from_bytes(cv_bytes, filename)
        if len(cv_text.strip()) < 50:
            raise ValueError("CV text too short — check PDF/DOCX is readable.")

        locations = options.locations or yaml_cfg.get("locations", ["Pakistan"])
        profile = extract_profile(cv_text, location_hints=locations)

        queries = generate_search_queries(profile, locations)
        results_per_query = yaml_cfg.get("jobs", {}).get("results_per_query", 15)
        min_score = options.min_match_score
        if min_score is None:
            min_score = yaml_cfg.get("jobs", {}).get("min_match_score_export", 0)

        provider = JSearchProvider()
        all_jobs = []
        # Search primary location + optional city variants (cap API calls)
        search_locations = locations[:3] if len(locations) > 3 else locations

        for query in queries:
            for loc in search_locations:
                batch = await provider.search(query, loc, results_per_query)
                all_jobs.extend(batch)
                await asyncio.sleep(0.3)

        deduped = dedupe_jobs(all_jobs)
        matched = match_jobs(profile, deduped)
        filtered = [j for j in matched if j.match_score >= min_score]

        sheet_id: str | None = None
        sheet_url: str | None = None
        if filtered:
            try:
                sheet_id, sheet_url = export_jobs_to_sheet(
                    filtered,
                    run_id,
                    sheet_title_suffix=run_id[:8],
                )
            except Exception as exc:
                sheet_id = None
                sheet_url = None
                sheet_fail_reason = str(exc)
            else:
                sheet_fail_reason = None
        else:
            sheet_fail_reason = None

        message = "Stage 1 completed successfully."
        if not filtered:
            message = "No jobs met the match score threshold."
        elif not sheet_url and sheet_fail_reason:
            message = f"Jobs matched but Google Sheet export failed: {sheet_fail_reason}"
        elif not sheet_url:
            message = "Jobs matched; configure Google Sheets to export."

        for job in filtered:
            db.add(
                JobRecord(
                    run_id=run_id,
                    job_id=job.job_id,
                    job_url=job.job_url,
                    title=job.job_title,
                    company=job.company,
                    match_score=job.match_score,
                    payload_json=job.model_dump_json(),
                )
            )

        result = Stage1RunResult(
            run_id=run_id,
            jobs_found=len(deduped),
            jobs_exported=len(filtered),
            sheet_url=sheet_url,
            sheet_id=sheet_id,
            profile=profile,
            message=message,
        )

        record.status = "completed"
        record.completed_at = datetime.utcnow()
        record.result_json = result.model_dump_json()
        db.commit()
        return result

    except Exception as exc:
        record.status = "failed"
        record.completed_at = datetime.utcnow()
        record.error = str(exc)
        db.commit()
        raise


def run_stage1_pipeline_sync(
    cv_bytes: bytes,
    filename: str,
    db: Session,
    options: Stage1RunRequest | None = None,
) -> Stage1RunResult:
    return asyncio.run(run_stage1_pipeline(cv_bytes, filename, db, options))


def get_run_result(db: Session, run_id: str) -> Stage1RunResult | None:
    row = db.get(RunRecord, run_id)
    if not row or not row.result_json:
        return None
    return Stage1RunResult.model_validate_json(row.result_json)
