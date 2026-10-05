from __future__ import annotations

import json

from openai import OpenAI

from app.config import get_settings, load_yaml_config
from app.models.schemas import (
    CandidateProfile,
    JobListing,
    MatchBatchItem,
    MatchBatchResult,
    MatchedJob,
)

_SYSTEM = (
    "Score each job 0-100 for fit with the candidate for applying. "
    "Be realistic for Pakistan / remote roles. "
    "Return every job_id from the input. Keep match_reason under 12 words."
)


def _keyword_prefilter(profile: CandidateProfile, jobs: list[JobListing], limit: int) -> list[JobListing]:
    tokens = set()
    for s in profile.skills + profile.keywords + profile.job_titles:
        for part in s.lower().replace("/", " ").split():
            if len(part) > 2:
                tokens.add(part)

    def score(job: JobListing) -> int:
        blob = f"{job.job_title} {job.company} {job.description_snippet or ''}".lower()
        return sum(1 for t in tokens if t in blob)

    ranked = sorted(jobs, key=score, reverse=True)
    return ranked[:limit]


def _chunks(items: list[JobListing], size: int) -> list[list[JobListing]]:
    if size < 1:
        size = 15
    return [items[i : i + size] for i in range(0, len(items), size)]


def _score_batch(
    client: OpenAI,
    model: str,
    profile: CandidateProfile,
    batch: list[JobListing],
) -> dict[str, MatchBatchItem]:
    job_payload = [
        {
            "job_id": j.job_id,
            "job_title": j.job_title,
            "company": j.company,
            "location": j.location,
            "source": j.source,
            "snippet": (j.description_snippet or "")[:200],
        }
        for j in batch
    ]
    # Compact profile for each batch (avoid huge repeated payloads)
    profile_compact = {
        "headline": profile.headline,
        "skills": profile.skills[:20],
        "job_titles": profile.job_titles[:10],
        "seniority": profile.seniority,
        "years_experience": profile.years_experience,
        "keywords": profile.keywords[:15],
    }

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {"profile": profile_compact, "jobs": job_payload},
                    ensure_ascii=False,
                ),
            },
        ],
        response_format=MatchBatchResult,
        temperature=0.2,
        max_tokens=4096,
    )
    parsed = completion.choices[0].message.parsed
    if not parsed:
        return {}
    return {m.job_id: m for m in parsed.matches}


def match_jobs(
    profile: CandidateProfile,
    jobs: list[JobListing],
    max_to_score: int | None = None,
) -> list[MatchedJob]:
    settings = get_settings()
    yaml_cfg = load_yaml_config(settings)
    jobs_cfg = yaml_cfg.get("jobs", {})
    matching_cfg = yaml_cfg.get("matching", {})
    cap = max_to_score or jobs_cfg.get("max_jobs_to_score", 80)
    batch_size = int(matching_cfg.get("batch_size", 15))

    subset = _keyword_prefilter(profile, jobs, cap)
    if not subset:
        return []

    if not settings.openai_api_key:
        return [
            MatchedJob(**j.model_dump(), match_score=50, match_reason="OpenAI key missing; neutral score")
            for j in subset
        ]

    model = matching_cfg.get("openai_model", "gpt-4o-mini")
    client = OpenAI(api_key=settings.openai_api_key)

    scores: dict[str, MatchBatchItem] = {}
    for batch in _chunks(subset, batch_size):
        try:
            scores.update(_score_batch(client, model, profile, batch))
        except Exception:
            # Soft-fail one batch; remaining batches still score
            continue

    matched: list[MatchedJob] = []
    for job in subset:
        m = scores.get(job.job_id)
        if m:
            matched.append(
                MatchedJob(
                    **job.model_dump(),
                    match_score=m.match_score,
                    match_reason=m.match_reason,
                )
            )
        else:
            matched.append(
                MatchedJob(**job.model_dump(), match_score=40, match_reason="Not scored by model")
            )
    matched.sort(key=lambda x: x.match_score, reverse=True)
    return matched
