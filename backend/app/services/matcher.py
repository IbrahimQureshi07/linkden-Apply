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


def match_jobs(
    profile: CandidateProfile,
    jobs: list[JobListing],
    max_to_score: int | None = None,
) -> list[MatchedJob]:
    settings = get_settings()
    yaml_cfg = load_yaml_config(settings)
    cap = max_to_score or yaml_cfg.get("jobs", {}).get("max_jobs_to_score", 80)

    subset = _keyword_prefilter(profile, jobs, cap)
    if not subset:
        return []

    if not settings.openai_api_key:
        return [
            MatchedJob(**j.model_dump(), match_score=50, match_reason="OpenAI key missing; neutral score")
            for j in subset
        ]

    model = yaml_cfg.get("matching", {}).get("openai_model", "gpt-4o-mini")
    client = OpenAI(api_key=settings.openai_api_key)

    job_payload = [
        {
            "job_id": j.job_id,
            "job_title": j.job_title,
            "company": j.company,
            "location": j.location,
            "source": j.source,
            "snippet": (j.description_snippet or "")[:400],
        }
        for j in subset
    ]

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Score each job 0-100 for fit with the candidate profile for applying. "
                    "Be realistic for Pakistan / remote roles. One short reason per job."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"profile": profile.model_dump(), "jobs": job_payload},
                    ensure_ascii=False,
                )[:100000],
            },
        ],
        response_format=MatchBatchResult,
        temperature=0.2,
    )
    parsed = completion.choices[0].message.parsed
    scores: dict[str, MatchBatchItem] = {}
    if parsed:
        scores = {m.job_id: m for m in parsed.matches}

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
