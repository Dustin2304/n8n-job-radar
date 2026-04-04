from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class JobResult(BaseModel):
    title: str = Field(description="Job title as listed in the posting")
    company: str = Field(description="Name of the hiring company")
    location: str = Field(description="Job location (city, country, or 'Remote')")
    url: str = Field(description="Direct link to the job posting")
    source: Literal["indeed", "linkedin"] = Field(description="Platform where the job was found")
    date_posted: str = Field(description="Posting date as returned by the source platform")
    is_remote: bool = Field(description="Whether the position is fully or partially remote")
    description: str = Field(max_length=500, description="Short excerpt of the job description (max 500 characters)")
    level: str = Field(description="Seniority level inferred from the posting")
    profile: str = Field(description="Search profile this job was matched to")
    in_watchlist: bool = Field(default=False, description="Whether the job has been saved to the watchlist")
    skills_required: list[str] = Field(
        default_factory=list,
        description="List of required skills extracted from the posting; empty if not determinable",
    )
    score: int = Field(default=0, description="Relevance score 0-100 computed by rule-based scorer")
    score_reason: str = Field(default="", description="Short human-readable reason for the score")


class ScrapeResponse(BaseModel):
    jobs: list[JobResult] = Field(description="All jobs returned after filtering")
    total_found: int = Field(description="Total number of raw results fetched before any filtering")
    total_after_filter: int = Field(description="Number of jobs remaining after deduplication and filters")
    scraped_at: datetime = Field(description="UTC timestamp of when the scrape was executed")
    profiles_searched: list[str] = Field(description="Search profiles that were active during this scrape run")


__all__ = ["JobResult", "ScrapeResponse"]
