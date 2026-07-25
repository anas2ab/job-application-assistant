from config import (
    BONUS_KEYWORDS,
    EXCLUDED_KEYWORDS,
    PREFERRED_LOCATIONS,
    REQUIRED_KEYWORDS,
    TARGET_TITLES,
)
from models import Job


def contains_keyword(text: str, keyword: str) -> bool:
    return keyword.lower() in text.lower()


def determine_work_type(job: Job) -> str:
    text = f"{job.location} {job.description}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "On-site"


def score_job(job: Job) -> int:
    title = job.title.lower()
    location = job.location.lower()
    full_text = f"{job.title} {job.description}".lower()

    if any(word in title for word in EXCLUDED_KEYWORDS):
        return 0

    score = 0

    # Job-title alignment: up to 35 points
    if any(target == title for target in TARGET_TITLES):
        score += 35
    elif any(target in title for target in TARGET_TITLES):
        score += 28
    elif "software engineer" in title:
        score += 20

    # Required technology alignment: up to 35 points
    required_matches = sum(
        1 for keyword in REQUIRED_KEYWORDS
        if contains_keyword(full_text, keyword)
    )

    if REQUIRED_KEYWORDS:
        score += round(
            35 * required_matches / len(REQUIRED_KEYWORDS)
        )

    # Bonus skills: up to 15 points
    bonus_matches = sum(
        1 for keyword in BONUS_KEYWORDS
        if contains_keyword(full_text, keyword)
    )

    score += min(15, bonus_matches * 3)

    # Location: up to 15 points
    if any(place in location for place in PREFERRED_LOCATIONS):
        score += 15
    elif "canada" in full_text or "remote" in full_text:
        score += 10

    job.work_type = determine_work_type(job)
    job.score = min(score, 100)

    return job.score