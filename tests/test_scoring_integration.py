from api.scorer import score_job
from api.models import JobResult


def make_job(title: str, profile: str, description: str = "") -> JobResult:
    return JobResult(
        title=title,
        company="Example Corp",
        location="Karlsruhe, Germany",
        url="https://example.com/job",
        source="linkedin",
        date_posted="2026-04-21",
        is_remote=False,
        description=description,
        level="Entry",
        profile=profile,
        in_watchlist=False,
        skills_required=[],
    )


def test_score_job_applies_weight():
    job = make_job("AI Engineer", "AI & Data Engineering", description="Python, LLM, FastAPI, MLOps")

    full_score, _ = score_job(job, weight=1.0)
    weighted_score, _ = score_job(job, weight=0.6)

    assert weighted_score <= full_score


def test_score_job_ai_title_above_it_threshold():
    job = make_job("AI Engineer", "AI & Data Engineering", description="Python and LLM platform work")

    score, _ = score_job(job, weight=1.0)

    assert score >= 50


def test_score_job_irrelevant_title_below_threshold():
    job = make_job("Hausmeister", "AI & Data Engineering", description="Building maintenance and cleaning")

    score, _ = score_job(job, weight=1.0)

    assert score < 50
