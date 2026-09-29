from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

import httpx

from app.config import get_settings
from app.models.schemas import ApplyType, JobListing
from app.services.job_providers.base import JobProvider


def _stable_job_id(url: str, title: str, company: str) -> str:
    raw = f"{url}|{title}|{company}".lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _normalize_source(publisher: str | None, apply_link: str | None, job_link: str | None) -> str:
    blob = " ".join(filter(None, [publisher, apply_link, job_link])).lower()
    if "linkedin" in blob:
        return "linkedin"
    if "indeed" in blob:
        return "indeed"
    if "glassdoor" in blob:
        return "glassdoor"
    if "ziprecruiter" in blob:
        return "ziprecruiter"
    if publisher:
        return re.sub(r"[^a-z0-9]+", "_", publisher.lower()).strip("_")[:32]
    return "unknown"


def _infer_apply_type(item: dict) -> tuple[ApplyType, str | None, str | None]:
    apply_options = item.get("apply_options") or []
    job_link = item.get("job_apply_link") or item.get("job_google_link") or ""
    apply_link = item.get("job_apply_link")

    easy = False
    external = False
    external_url: str | None = None

    for opt in apply_options:
        if not isinstance(opt, dict):
            continue
        publisher = (opt.get("publisher") or "").lower()
        link = opt.get("apply_link") or opt.get("link") or ""
        if "linkedin" in publisher and link:
            easy = True
        elif link and link != job_link:
            external = True
            external_url = link

    desc = (item.get("job_description") or "").lower()
    if "easy apply" in desc or "linkedin" in desc and "apply" in desc:
        easy = True

    if not apply_link and external_url:
        apply_link = external_url

    host = urlparse(job_link or "").netloc.lower()
    if "linkedin.com" in host:
        easy = True

    if easy and external:
        apply_type = ApplyType.BOTH
        note = "Easy Apply (LinkedIn) and external apply links detected"
    elif easy:
        apply_type = ApplyType.EASY_APPLY
        note = "Likely Easy Apply (LinkedIn / Google Jobs)"
    elif external or (apply_link and apply_link != job_link):
        apply_type = ApplyType.EXTERNAL
        note = "Apply on company / external site"
    else:
        apply_type = ApplyType.UNKNOWN
        note = None

    return apply_type, apply_link, note


def _jobs_from_payload(payload: dict) -> list:
    """JSearch /search-v2 returns data.jobs; older /search returned data as a list."""
    data = (payload or {}).get("data")
    if isinstance(data, dict):
        jobs = data.get("jobs")
        return jobs if isinstance(jobs, list) else []
    if isinstance(data, list):
        return data
    return []


class JSearchProvider(JobProvider):
    BASE_URL = "https://jsearch.p.rapidapi.com/search-v2"

    async def search(
        self,
        query: str,
        location: str,
        num_results: int,
    ) -> list[JobListing]:
        settings = get_settings()
        if not settings.rapidapi_key:
            raise ValueError("RAPIDAPI_KEY is not set (JSearch on RapidAPI).")

        headers = {
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": settings.rapidapi_host,
        }
        # Prefer "title + location" in query (matches RapidAPI examples)
        search_query = f"{query} in {location}".strip() if location else query
        params = {
            "query": search_query,
            "num_pages": "1",
            "country": "pk",
            "date_posted": "all",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(self.BASE_URL, headers=headers, params=params)
            resp.raise_for_status()
            payload = resp.json()

        data = _jobs_from_payload(payload)
        listings: list[JobListing] = []
        for item in data[:num_results]:
            title = item.get("job_title") or "Unknown title"
            company = item.get("employer_name") or "Unknown company"
            loc = item.get("job_city") or item.get("job_country") or location
            if item.get("job_is_remote"):
                loc = f"{loc} (Remote)".strip()

            job_url = (
                item.get("job_apply_link")
                or item.get("job_google_link")
                or item.get("job_link")
                or ""
            )
            if not job_url:
                continue

            apply_type, apply_url, note = _infer_apply_type(item)
            source = _normalize_source(
                item.get("job_publisher"),
                apply_url,
                job_url,
            )

            salary = None
            if item.get("job_min_salary") or item.get("job_max_salary"):
                mn = item.get("job_min_salary")
                mx = item.get("job_max_salary")
                cur = item.get("job_salary_currency") or ""
                salary = f"{mn}-{mx} {cur}".strip()

            snippet = (item.get("job_description") or "")[:500] or None
            posted = item.get("job_posted_at_datetime_utc") or item.get("job_posted_at")

            listings.append(
                JobListing(
                    job_id=_stable_job_id(job_url, title, company),
                    job_title=title,
                    company=company,
                    location=str(loc),
                    posted_at=str(posted) if posted else None,
                    source=source,
                    apply_type=apply_type,
                    job_url=job_url,
                    apply_url=apply_url if apply_url != job_url else None,
                    easy_apply_note=note,
                    salary=salary,
                    description_snippet=snippet,
                    search_query=query,
                )
            )
        return listings
