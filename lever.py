import re
from typing import List

import requests

from models import Job


def clean_text(value: str) -> str:
    if not value:
        return ""

    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def fetch_lever_jobs(
    company_name: str,
    site_token: str,
) -> List[Job]:
    url = f"https://api.lever.co/v0/postings/{site_token}?mode=json"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    results: List[Job] = []

    for item in response.json():
        categories = item.get("categories", {})
        location = categories.get("location", "")

        description_parts = [
            item.get("descriptionPlain", ""),
            item.get("additionalPlain", ""),
        ]

        results.append(
            Job(
                company=company_name,
                title=item.get("text", ""),
                location=location,
                url=item.get("hostedUrl", ""),
                source="Lever",
                description=clean_text(" ".join(description_parts)),
            )
        )

    return results