from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ApplyType(str, Enum):
    EASY_APPLY = "easy_apply"
    EXTERNAL = "external"
    BOTH = "both"
    UNKNOWN = "unknown"


class CandidateProfile(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    job_titles: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    years_experience: float | None = None
    seniority: str | None = None
    location_preferences: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class JobListing(BaseModel):
    job_id: str
    job_title: str
    company: str
    location: str
    posted_at: str | None = None
    source: str = "unknown"
    apply_type: ApplyType = ApplyType.UNKNOWN
    job_url: str
    apply_url: str | None = None
    easy_apply_note: str | None = None
    salary: str | None = None
    description_snippet: str | None = None
    search_query: str | None = None


class MatchedJob(JobListing):
    match_score: int = 0
    match_reason: str = ""


class SearchQueries(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=12)


class MatchBatchItem(BaseModel):
    job_id: str
    match_score: int = Field(ge=0, le=100)
    match_reason: str


class MatchBatchResult(BaseModel):
    matches: list[MatchBatchItem]


class Stage1RunRequest(BaseModel):
    locations: list[str] | None = None
    remote_only: bool | None = None
    min_match_score: int | None = None


class Stage1RunResult(BaseModel):
    run_id: str
    jobs_found: int
    jobs_exported: int
    sheet_url: str | None = None
    sheet_id: str | None = None
    profile: CandidateProfile
    message: str = ""


class RunStatusResponse(BaseModel):
    run_id: str
    status: Literal["pending", "running", "completed", "failed"]
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    result: Stage1RunResult | None = None
