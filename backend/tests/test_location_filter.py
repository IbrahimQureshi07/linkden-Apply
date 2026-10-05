from app.models.schemas import ApplyType, JobListing
from app.services.location_filter import filter_jobs_by_locations, job_matches_locations


def _job(location: str) -> JobListing:
    return JobListing(
        job_id="x",
        job_title="Engineer",
        company="Co",
        location=location,
        job_url="https://example.com/j/1",
        apply_type=ApplyType.UNKNOWN,
    )


def test_karachi_only():
    assert job_matches_locations(_job("Karachi, Pakistan"), ["Karachi"])
    assert not job_matches_locations(_job("Lahore"), ["Karachi"])
    assert not job_matches_locations(_job("Rawalpindi"), ["Karachi"])


def test_karachi_and_lahore():
    locs = ["Karachi", "Lahore"]
    assert job_matches_locations(_job("Karachi"), locs)
    assert job_matches_locations(_job("Lahore, PK"), locs)
    assert not job_matches_locations(_job("Islamabad"), locs)


def test_pakistan_country_wide():
    assert job_matches_locations(_job("Lahore"), ["Pakistan"])
    assert job_matches_locations(_job("Multan"), ["Pakistan"])
    assert job_matches_locations(_job("Karachi"), ["Pakistan"])


def test_remote_or_city():
    locs = ["Karachi", "Remote"]
    assert job_matches_locations(_job("Karachi"), locs)
    assert job_matches_locations(_job("Remote — Worldwide"), locs)
    assert not job_matches_locations(_job("Lahore"), locs)


def test_filter_list():
    from app.models.schemas import MatchedJob

    jobs = [
        MatchedJob(**_job("Karachi").model_dump(), match_score=80, match_reason="ok"),
        MatchedJob(**_job("Lahore").model_dump(), match_score=80, match_reason="ok"),
    ]
    out = filter_jobs_by_locations(jobs, ["Karachi"])
    assert len(out) == 1
    assert "Karachi" in out[0].location
