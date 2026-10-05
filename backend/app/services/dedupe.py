from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse, urlunparse

from app.models.schemas import JobListing


def normalize_job_url(url: str) -> str:
    return _normalize_url(url)


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip().lower())
    netloc = parsed.netloc.replace("www.", "")
    path = parsed.path.rstrip("/")
    qs = parse_qs(parsed.query)
    keep = {}
    for key in ("id", "jobId", "currentJobId"):
        if key in qs:
            keep[key] = qs[key]
    query = ""
    if keep:
        parts = []
        for k, v in keep.items():
            parts.append(f"{k}={v[0]}")
        query = "&".join(parts)
    return urlunparse((parsed.scheme, netloc, path, "", query, ""))


def _norm_title_company(title: str, company: str) -> str:
    t = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    c = re.sub(r"[^a-z0-9]+", " ", company.lower()).strip()
    return f"{t}|{c}"


def dedupe_jobs(jobs: list[JobListing]) -> list[JobListing]:
    by_url: dict[str, JobListing] = {}
    by_tc: dict[str, JobListing] = {}

    for job in jobs:
        url_key = _normalize_url(job.job_url)
        tc_key = _norm_title_company(job.job_title, job.company)

        existing = by_url.get(url_key) or by_tc.get(tc_key)
        if existing is None:
            by_url[url_key] = job
            by_tc[tc_key] = job
            continue

        # Merge: prefer linkedin source, higher detail
        merged = _merge_jobs(existing, job)
        by_url[url_key] = merged
        by_tc[tc_key] = merged

    seen_ids: set[str] = set()
    out: list[JobListing] = []
    for job in by_url.values():
        if job.job_id in seen_ids:
            continue
        seen_ids.add(job.job_id)
        out.append(job)
    return out


def _merge_jobs(a: JobListing, b: JobListing) -> JobListing:
    data = a.model_dump()
    other = b.model_dump()
    for key, val in other.items():
        if key == "apply_type":
            data[key] = _merge_apply_type(a.apply_type, b.apply_type)
            continue
        if not data.get(key) and val:
            data[key] = val
        if key == "source" and val == "linkedin":
            data[key] = val
    return JobListing.model_validate(data)


def _merge_apply_type(a, b):
    from app.models.schemas import ApplyType

    if a == ApplyType.BOTH or b == ApplyType.BOTH:
        return ApplyType.BOTH
    if a == b:
        return a
    if a == ApplyType.UNKNOWN:
        return b
    if b == ApplyType.UNKNOWN:
        return a
    return ApplyType.BOTH
