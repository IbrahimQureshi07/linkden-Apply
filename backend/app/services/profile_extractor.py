from __future__ import annotations

from openai import OpenAI

from app.config import get_settings, load_yaml_config
from app.models.schemas import CandidateProfile


SYSTEM_PROMPT = """You extract structured job-search profile data from a CV/resume.
Return accurate skills, likely job titles to search for, seniority, and keywords.
Prefer Pakistan-relevant titles when the CV suggests local or remote work unless the CV clearly targets another market."""


def extract_profile(cv_text: str, location_hints: list[str] | None = None) -> CandidateProfile:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set.")

    yaml_cfg = load_yaml_config(settings)
    model = yaml_cfg.get("profile", {}).get("openai_model", "gpt-4o-mini")
    locs = location_hints or yaml_cfg.get("locations", ["Pakistan"])

    client = OpenAI(api_key=settings.openai_api_key)
    user_content = f"Target locations for job search: {', '.join(locs)}\n\nCV:\n{cv_text[:120000]}"

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format=CandidateProfile,
        temperature=0.2,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no structured profile.")
    if not parsed.job_titles and parsed.headline:
        parsed.job_titles = [parsed.headline]
    if not parsed.keywords:
        parsed.keywords = parsed.skills[:15]
    return parsed
