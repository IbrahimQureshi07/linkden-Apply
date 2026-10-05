from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import JobRecord
from app.models.schemas import MatchedJob
from app.services.dedupe import normalize_job_url


def previously_exported_keys(db: Session) -> tuple[set[str], set[str]]:
    """Return (job_ids, normalized_urls) already written on a past successful export."""
    rows = db.execute(select(JobRecord.job_id, JobRecord.job_url)).all()
    ids: set[str] = set()
    urls: set[str] = set()
    for job_id, job_url in rows:
        if job_id:
            ids.add(job_id)
        if job_url:
            urls.add(normalize_job_url(job_url))
    return ids, urls


def filter_new_jobs_for_export(
    jobs: list[MatchedJob],
    db: Session,
) -> tuple[list[MatchedJob], int]:
    """Drop jobs already exported in earlier runs. Returns (new_jobs, skipped_count)."""
    seen_ids, seen_urls = previously_exported_keys(db)
    fresh: list[MatchedJob] = []
    skipped = 0
    for job in jobs:
        url_key = normalize_job_url(job.job_url)
        if job.job_id in seen_ids or url_key in seen_urls:
            skipped += 1
            continue
        fresh.append(job)
    return fresh, skipped
