from __future__ import annotations

from openai import OpenAI

from app.config import get_settings, load_yaml_config
from app.models.schemas import CandidateProfile, SearchQueries


def generate_search_queries(
    profile: CandidateProfile,
    locations: list[str],
    max_queries: int | None = None,
) -> list[str]:
    settings = get_settings()
    yaml_cfg = load_yaml_config(settings)
    cap = max_queries or yaml_cfg.get("jobs", {}).get("max_queries", 8)

    if not settings.openai_api_key:
        return _fallback_queries(profile, cap)

    model = yaml_cfg.get("profile", {}).get("openai_model", "gpt-4o-mini")
    client = OpenAI(api_key=settings.openai_api_key)

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate diverse job board search queries for finding roles matching this candidate. "
                    "Mix exact titles and broader queries. No location in query string (location passed separately). "
                    f"Return at most {cap} queries."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Locations: {', '.join(locations)}\n"
                    f"Profile JSON: {profile.model_dump_json()}"
                ),
            },
        ],
        response_format=SearchQueries,
        temperature=0.4,
    )
    parsed = completion.choices[0].message.parsed
    if parsed and parsed.queries:
        return parsed.queries[:cap]
    return _fallback_queries(profile, cap)


def _fallback_queries(profile: CandidateProfile, cap: int) -> list[str]:
    queries: list[str] = []
    for title in profile.job_titles[: cap // 2 or 1]:
        queries.append(title)
    if profile.skills:
        top = " ".join(profile.skills[:3])
        queries.append(f"{top} developer")
    if profile.headline:
        queries.append(profile.headline)
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        key = q.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(q.strip())
        if len(out) >= cap:
            break
    return out or ["software engineer"]
