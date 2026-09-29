from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.schemas import JobListing


class JobProvider(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        location: str,
        num_results: int,
    ) -> list[JobListing]:
        raise NotImplementedError
