"""
api/scorer.py
Rule-based pre-scorer for JobResult objects.
Computes a deterministic score 0-100 and a short reason string.
The LLM in n8n only needs to generate/confirm the reason afterwards.
"""

from __future__ import annotations

from .models import JobResult

TITLE_KEYWORDS: list[tuple[int, list[str]]] = [
    (35, [
        "ai engineer",
        "ml engineer",
        "llm engineer",
        "genai developer",
        "ki entwickler",
        "ai developer",
        "prompt engineer",
        "mlops",
    ]),
    (30, [
        "data scientist",
        "data engineer",
        "machine learning",
        "deep learning",
        "nlp engineer",
        "computer vision",
        "analytics engineer",
    ]),
    (25, [
        "software engineer",
        "software developer",
        "backend developer",
        "backend engineer",
        "fullstack developer",
        "full stack engineer",
        "python developer",
        "typescript developer",
        "platform engineer",
    ]),
    (22, [
        "data analyst",
        "bi developer",
        "business intelligence",
        "data warehouse",
        "data platform",
        "reporting analyst",
    ]),
    (20, [
        "cloud engineer",
        "devops engineer",
        "rpa developer",
        "automatisierung entwickler",
        "api developer",
    ]),
    (20, [
        "it consultant",
        "digitalisierungsmanager",
        "digitalization manager",
        "business analyst it",
        "implementation consultant",
    ]),
    (18, [
        "iot developer",
        "mes entwickler",
        "industrie 4.0",
        "ot engineer",
        "digital factory",
        "smart manufacturing",
    ]),
    (18, [
        "supply chain it",
        "logistik it",
        "wms developer",
        "warehouse management",
    ]),
    (18, [
        "finance it",
        "controlling it",
        "financial analyst it",
        "fp&a analyst",
        "accounting software",
    ]),
    (18, [
        "martech",
        "marketing technology",
        "e-commerce developer",
        "crm developer",
        "marketing automation",
        "growth engineer",
    ]),
    (10, [
        "sales engineer",
        "technical sales",
        "pre-sales consultant",
        "business development",
        "solution sales",
    ]),
    (8, ["performance marketing", "product marketing", "content manager"]),
    (8, ["operations analyst", "procurement analyst"]),
]

DESCRIPTION_KEYWORDS: list[tuple[int, list[str]]] = [
    (12, [
        "llm",
        "large language model",
        "generative ai",
        "genai",
        "gpt",
        "langchain",
        "rag",
        "copilot",
        "openai",
        "azure ai",
    ]),
    (10, [
        "machine learning",
        "deep learning",
        "neural network",
        "pytorch",
        "tensorflow",
        "mlops",
        "hugging face",
    ]),
    (8, ["python", "fastapi", "django", "flask"]),
    (8, ["typescript", "node.js", "react", "vue"]),
    (6, ["docker", "kubernetes", "azure", "aws", "gcp", "cloud"]),
    (6, ["rest api", "microservices", "ci/cd", "devops"]),
    (5, ["automatisierung", "automation", "rpa", "workflow"]),
    (4, ["sql", "postgresql", "mongodb", "data pipeline"]),
]

WATCHLIST_BONUS = 8
JUNIOR_BONUS = 5
REMOTE_MALUS = 0


def _match_keywords(text: str, groups: list[tuple[int, list[str]]]) -> tuple[int, list[str]]:
    """Returns total points and matched keywords."""
    total = 0
    matched: list[str] = []
    text_lower = text.lower()
    for points, keywords in groups:
        for kw in keywords:
            if kw in text_lower:
                total += points
                matched.append(kw)
                break
    return total, matched


def _build_reason(
    title_matches: list[str],
    desc_matches: list[str],
    watchlist: bool,
    level: str,
    weight: float,
) -> str:
    """Build a short reason string from the strongest matches."""
    parts: list[str] = []

    if title_matches:
        parts.append(title_matches[0].title())

    for kw in desc_matches[:2]:
        label = kw.upper() if len(kw) <= 4 else kw.title()
        if label.lower() not in [p.lower() for p in parts]:
            parts.append(label)

    if watchlist:
        parts.append("Watchlist")
    if level in ("Entry", "Mid"):
        parts.append(level + "-Level")
    if weight < 1.0:
        parts.append("Non-IT")

    return ", ".join(parts[:5]) or "Kein klarer Match"


def score_job(job: JobResult, weight: float = 1.0) -> tuple[int, str]:
    """
    Returns (score: int 0-100, reason: str).
    Score 0 = definitively irrelevant.
    """
    title = job.title.lower()
    desc = (job.description or "").lower()

    title_pts, title_matches = _match_keywords(title, TITLE_KEYWORDS)

    desc_pts, desc_matches = _match_keywords(desc, DESCRIPTION_KEYWORDS)
    desc_pts = min(desc_pts, 25)

    base = 30
    raw = base + title_pts + desc_pts

    if job.in_watchlist:
        raw += WATCHLIST_BONUS
    if any(kw in title for kw in ("junior", "entry", "trainee", "werkstudent")):
        raw += JUNIOR_BONUS

    raw = int(raw * weight)

    score = max(0, min(100, raw))
    reason = _build_reason(title_matches, desc_matches, job.in_watchlist, job.level, weight)

    return score, reason
