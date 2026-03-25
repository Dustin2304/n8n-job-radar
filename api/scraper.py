#!/usr/bin/env python3
"""
api/scraper.py
Scrapes job postings via python-jobspy, driven entirely by config.yaml.
Returns a ScrapeResponse JSON to stdout (called from n8n Execute Command node).
"""

import json
import logging
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Path setup so models.py (project root) is importable ─────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml

try:
    from jobspy import scrape_jobs
except ImportError:
    print(json.dumps({"error": "python-jobspy not installed. Run: pip install python-jobspy"}))
    sys.exit(1)

from models import JobResult, ScrapeResponse

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
HOURS_OLD = 168        # 7 days
RESULTS_PER_SEARCH = 25
KM_TO_MILES = 0.621371

LEVEL_MAP = {
    "internship": "Entry",
    "entry level": "Entry",
    "entry-level": "Entry",
    "associate": "Entry",
    "junior": "Entry",
    "mid-senior level": "Mid",
    "mid level": "Mid",
    "mid-level": "Mid",
    "mid": "Mid",
    "senior": "Senior",
    "director": "Senior",
    "executive": "Senior",
    "c-suite": "Senior",
    "vice president": "Senior",
}


# ── Config loading ─────────────────────────────────────────────────────────────
def load_config() -> dict:
    config_path = ROOT / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Helpers ───────────────────────────────────────────────────────────────────
def company_in_watchlist(company_name: str, watchlist: list[str]) -> bool:
    if not company_name:
        return False
    name_lower = company_name.lower()
    return any(w.lower() in name_lower or name_lower in w.lower() for w in watchlist)


def map_level(raw_level: str | None) -> str:
    if not raw_level:
        return "Unknown"
    return LEVEL_MAP.get(raw_level.strip().lower(), "Unknown")


def should_exclude(title: str, job_level: str | None, exclude_cfg: dict) -> bool:
    title_lower = title.lower()
    for kw in exclude_cfg.get("title_keywords", []):
        if kw.lower() in title_lower:
            return True
    excluded_levels = [lvl.lower() for lvl in exclude_cfg.get("levels", [])]
    if job_level and job_level.strip().lower() in excluded_levels:
        return True
    return False


# ── Core scrape ───────────────────────────────────────────────────────────────
def run_scrape() -> ScrapeResponse:
    cfg = load_config()

    profiles: list[dict] = cfg["profiles"]
    locations: list[dict] = cfg["locations"]
    exclude_cfg: dict = cfg.get("exclude", {})
    watchlist: list[str] = [c["name"] for c in cfg.get("companies", [])]

    seen_urls: set[str] = set()
    seen_title_company: set[tuple[str, str]] = set()
    all_jobs: list[JobResult] = []
    total_raw = 0
    failed_searches = 0

    for profile in profiles:
        profile_name: str = profile["name"]
        keywords: list[str] = profile["keywords"]

        for keyword in keywords:
            for loc in locations:
                city: str = loc["city"]
                country: str = loc["country"]
                is_remote: bool = loc.get("is_remote", False)
                radius_km: int = loc.get("radius_km", 0)
                radius_miles = int(radius_km * KM_TO_MILES) if radius_km else None

                scrape_kwargs = dict(
                    site_name=["indeed", "linkedin"],
                    search_term=keyword,
                    location=city,
                    results_wanted=RESULTS_PER_SEARCH,
                    hours_old=HOURS_OLD,
                    country_indeed=country,
                    description_format="markdown",
                    verbose=0,
                )
                if is_remote:
                    scrape_kwargs["is_remote"] = True
                if radius_miles:
                    scrape_kwargs["distance"] = radius_miles

                try:
                    df = scrape_jobs(**scrape_kwargs)
                except Exception as exc:
                    log.warning("Search failed [%s / %s / %s]: %s", profile_name, keyword, city, exc)
                    failed_searches += 1
                    time.sleep(1.5)
                    continue

                if df is None or df.empty:
                    time.sleep(1.5)
                    continue

                total_raw += len(df)

                for _, row in df.iterrows():
                    url = str(row.get("job_url", "") or "").strip()
                    if not url or url in seen_urls:
                        continue

                    title = str(row.get("title", "") or "").strip()
                    company = str(row.get("company", "") or "").strip()
                    job_level_raw = str(row.get("job_level", "") or "").strip() or None

                    # Pre-filter before any further processing
                    if should_exclude(title, job_level_raw, exclude_cfg):
                        continue

                    # Dedup by title+company
                    dedup_key = (title.lower(), company.lower())
                    if dedup_key in seen_title_company:
                        continue

                    seen_urls.add(url)
                    seen_title_company.add(dedup_key)

                    description = str(row.get("description", "") or "")[:500]
                    source_raw = str(row.get("site", "") or "").lower()
                    source = source_raw if source_raw in ("indeed", "linkedin") else "indeed"

                    job = JobResult(
                        title=title,
                        company=company,
                        location=str(row.get("location", "") or ""),
                        url=url,
                        source=source,
                        date_posted=str(row.get("date_posted", "") or ""),
                        is_remote=bool(row.get("is_remote", False)),
                        description=description,
                        level=map_level(job_level_raw),
                        profile=profile_name,
                        in_watchlist=company_in_watchlist(company, watchlist),
                        skills_required=[],
                    )
                    all_jobs.append(job)

                time.sleep(1.5)

    log.info(
        "Scrape complete: %d raw results → %d after filter/dedup | %d searches failed",
        total_raw,
        len(all_jobs),
        failed_searches,
    )

    return ScrapeResponse(
        jobs=all_jobs,
        total_found=total_raw,
        total_after_filter=len(all_jobs),
        scraped_at=datetime.now(timezone.utc),
        profiles_searched=[p["name"] for p in profiles],
    )


if __name__ == "__main__":
    response = run_scrape()
    print(response.model_dump_json(indent=None))
