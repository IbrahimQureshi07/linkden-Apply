"""Optional SerpAPI Google Jobs provider — enable when SERPAPI_KEY is added."""

from __future__ import annotations

from app.models.schemas import JobListing
from app.services.job_providers.base import JobProvider


class SerpGoogleJobsProvider(JobProvider):
    async def search(
        self,
        query: str,
        location: str,
        num_results: int,
    ) -> list[JobListing]:
        raise NotImplementedError(
            "SerpAPI provider is a stub. Use JSearchProvider for MVP or implement with SERPAPI_KEY."
        )
