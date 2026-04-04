"""
api/scorer.py
Rule-based pre-scorer for JobResult objects.
Computes a deterministic score 0-100 and a short reason string.
The LLM in n8n only needs to generate/confirm the reason afterwards.
"""

from __future__ import annotations
from models import JobResult

# ── Gewichtete Keyword-Listen (Titel schlägt Description) ────────────────────

TITLE_KEYWORDS: list[tuple[int, list[str]]] = [
    # (Punkte, Keywords)
    (35, ["ai engineer", "ml engineer", "llm engineer", "genai developer",
          "ki entwickler", "ai developer", "prompt engineer", "mlops"]),
    (30, ["data scientist", "data engineer", "machine learning", "deep learning",
          "nlp engineer", "computer vision", "analytics engineer"]),
    (25, ["software engineer", "software developer", "backend developer",
          "backend engineer", "fullstack developer", "full stack engineer",
          "python developer", "typescript developer", "platform engineer"]),
    (22, ["data analyst", "bi developer", "business intelligence",
          "data warehouse", "data platform", "reporting analyst"]),
    (20, ["cloud engineer", "devops engineer", "rpa developer",
          "automatisierung entwickler", "api developer"]),
    (20, ["it consultant", "digitalisierungsmanager", "digitalization manager",
          "business analyst it", "implementation consultant"]),
    (18, ["iot developer", "mes entwickler", "industrie 4.0", "ot engineer",
          "digital factory", "smart manufacturing"]),
    (18, ["supply chain it", "logistik it", "wms developer",
          "warehouse management"]),
    (18, ["finance it", "controlling it", "financial analyst it",
          "fp&a analyst", "accounting software"]),
    (18, ["martech", "marketing technology", "e-commerce developer",
          "crm developer", "marketing automation", "growth engineer"]),
    # Non-IT (niedrigere Basis)
    (10, ["sales engineer", "technical sales", "pre-sales consultant",
          "business development", "solution sales"]),
    (8,  ["performance marketing", "product marketing", "content manager"]),
    (8,  ["operations analyst", "procurement analyst"]),
]

DESCRIPTION_KEYWORDS: list[tuple[int, list[str]]] = [
    (12, ["llm", "large language model", "generative ai", "genai", "gpt",
          "langchain", "rag", "copilot", "openai", "azure ai"]),
    (10, ["machine learning", "deep learning", "neural network", "pytorch",
          "tensorflow", "mlops", "hugging face"]),
    (8,  ["python", "fastapi", "django", "flask"]),
    (8,  ["typescript", "node.js", "react", "vue"]),
    (6,  ["docker", "kubernetes", "azure", "aws", "gcp", "cloud"]),
    (6,  ["rest api", "microservices", "ci/cd", "devops"]),
    (5,  ["automatisierung", "automation", "rpa", "workflow"]),
    (4,  ["sql", "postgresql", "mongodb", "data pipeline"]),
]

# Bonus / Malus
WATCHLIST_BONUS   = 8
JUNIOR_BONUS      = 5   # wenn "junior" oder "entry" im Titel
REMOTE_MALUS      = 0   # Remote wurde schon im Scraper gefiltert

NON_IT_PROFILES = {
    "Vertrieb & Business Development",
    "Marketing & Content",
    "Logistik & Operations",
}

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

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
                break  # nur einmal pro Gruppe zählen
    return total, matched


def _build_reason(title_matches: list[str], desc_matches: list[str],
                  watchlist: bool, level: str, profile: str) -> str:
    """Baut eine max. 8-Wort-Begründung aus den Matches."""
    parts: list[str] = []

    # Stärksten Title-Match zuerst
    if title_matches:
        parts.append(title_matches[0].title())

    # Bis zu 2 Description-Highlights
    for kw in desc_matches[:2]:
        label = kw.upper() if len(kw) <= 4 else kw.title()
        if label.lower() not in [p.lower() for p in parts]:
            parts.append(label)

    if watchlist:
        parts.append("Watchlist")
    if level in ("Entry", "Mid"):
        parts.append(level + "-Level")
    if profile in NON_IT_PROFILES:
        parts.append("Non-IT")

    return ", ".join(parts[:5]) or "Kein klarer Match"


# ── Haupt-Scoring-Funktion ────────────────────────────────────────────────────

def score_job(job: JobResult) -> tuple[int, str]:
    """
    Returns (score: int 0-100, reason: str).
    Score 0 = definitiv irrelevant (wird gefiltert bevor LLM es sieht).
    """
    title = job.title.lower()
    desc  = (job.description or "").lower()

    # ── Titel-Score ───────────────────────────────────────────────────────────
    title_pts, title_matches = _match_keywords(title, TITLE_KEYWORDS)

    # ── Description-Score (gedeckelt) ────────────────────────────────────────
    desc_pts, desc_matches = _match_keywords(desc, DESCRIPTION_KEYWORDS)
    desc_pts = min(desc_pts, 25)  # max 25 Punkte aus Description

    # ── Basis-Score ───────────────────────────────────────────────────────────
    base = 30  # Jeder Job der den Senior-Filter überlebt startet bei 30
    raw  = base + title_pts + desc_pts

    # ── Boni ─────────────────────────────────────────────────────────────────
    if job.in_watchlist:
        raw += WATCHLIST_BONUS
    if any(kw in title for kw in ("junior", "entry", "trainee", "werkstudent")):
        raw += JUNIOR_BONUS

    # ── Non-IT Malus ─────────────────────────────────────────────────────────
    if job.profile in NON_IT_PROFILES:
        raw = int(raw * 0.75)  # 25% Abzug für Non-IT Profile

    score  = max(0, min(100, raw))
    reason = _build_reason(title_matches, desc_matches,
                           job.in_watchlist, job.level, job.profile)

    return score, reason