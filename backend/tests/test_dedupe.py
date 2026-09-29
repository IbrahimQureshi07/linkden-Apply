from app.models.schemas import ApplyType, JobListing
from app.services.dedupe import dedupe_jobs


def test_dedupe_by_url():
    a = JobListing(
        job_id="1",
        job_title="Python Dev",
        company="Acme",
        location="Karachi",
        job_url="https://example.com/jobs/1?utm=1",
        source="linkedin",
        apply_type=ApplyType.EASY_APPLY,
    )
    b = JobListing(
        job_id="2",
        job_title="Python Dev",
        company="Acme",
        location="Karachi",
        job_url="https://example.com/jobs/1",
        source="indeed",
        apply_type=ApplyType.EXTERNAL,
    )
    out = dedupe_jobs([a, b])
    assert len(out) == 1
    assert out[0].apply_type == ApplyType.BOTH
