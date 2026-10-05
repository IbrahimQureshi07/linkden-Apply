from __future__ import annotations

import re

from app.models.schemas import JobListing, MatchedJob

_PAKISTAN_ALIASES = frozenset({"pakistan", "pk", "pak"})
_REMOTE_ALIASES = frozenset({"remote", "work from home", "wfh", "anywhere"})

# Common city spellings → canonical token used for matching
_CITY_ALIASES: dict[str, str] = {
    "karachi": "karachi",
    "khi": "karachi",
    "lahore": "lahore",
    "lhr": "lahore",
    "islamabad": "islamabad",
    "isb": "islamabad",
    "rawalpindi": "rawalpindi",
    "rwp": "rawalpindi",
    "pindi": "rawalpindi",
    "multan": "multan",
    "peshawar": "peshawar",
    "faisalabad": "faisalabad",
    "hyderabad": "hyderabad",
    "quetta": "quetta",
    "sialkot": "sialkot",
    "gujranwala": "gujranwala",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _canonicalize_location_token(token: str) -> str:
    t = _norm(token)
    if t in _PAKISTAN_ALIASES:
        return "pakistan"
    if t in _REMOTE_ALIASES:
        return "remote"
    return _CITY_ALIASES.get(t, t)


def parse_location_selection(locations: list[str]) -> tuple[bool, bool, list[str]]:
    """Returns (country_wide_pakistan, allow_remote, city_tokens)."""
    tokens = [_canonicalize_location_token(x) for x in locations if _norm(x)]
    country_wide = "pakistan" in tokens
    allow_remote = "remote" in tokens
    cities = [t for t in tokens if t not in {"pakistan", "remote"}]
    # unique keep order
    seen: set[str] = set()
    uniq_cities: list[str] = []
    for c in cities:
        if c not in seen:
            seen.add(c)
            uniq_cities.append(c)
    return country_wide, allow_remote, uniq_cities


def _job_is_remote(job: JobListing) -> bool:
    blob = _norm(f"{job.location} {job.description_snippet or ''}")
    return "remote" in blob or "work from home" in blob or "wfh" in blob


def job_matches_locations(job: JobListing, locations: list[str]) -> bool:
    """
    Strict export rules:
    - Pakistan (alone or with cities): allow any Pakistan-oriented result (country-wide).
    - Cities only (e.g. Karachi, Lahore): job.location must mention one of those cities.
    - Remote in list: also allow remote jobs (OR with cities / Pakistan).
    - Remote only: only remote jobs.
    """
    if not locations:
        return True

    country_wide, allow_remote, cities = parse_location_selection(locations)
    loc = _norm(job.location)
    remote = _job_is_remote(job)

    if allow_remote and remote:
        return True

    if country_wide:
        # Country-wide Pakistan search — keep job (API already scoped to pk).
        # Still drop obvious foreign-only labels if present without PK cities.
        foreign_hints = ("united states", "usa", "uk", "london", "dubai", "india", "canada")
        if any(h in loc for h in foreign_hints) and not any(
            c in loc for c in _CITY_ALIASES.values()
        ) and "pakistan" not in loc and loc not in {"pk", "pak"}:
            return allow_remote and remote
        return True

    if not cities:
        # Only remote was selected (or empty after parse)
        return bool(allow_remote and remote)

    # City-strict: must mention a selected city
    for city in cities:
        if city in loc:
            return True
        # Canonical alias reverse: "Karachi (Remote)" etc.
        for alias, canon in _CITY_ALIASES.items():
            if canon == city and alias in loc:
                return True
    return False


def filter_jobs_by_locations(
    jobs: list[MatchedJob],
    locations: list[str],
) -> list[MatchedJob]:
    return [j for j in jobs if job_matches_locations(j, locations)]
