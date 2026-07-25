import html
import re
from typing import List

import requests

from models import Job


def clean_html(value: str) -> str:
    if not value:
        return ""

    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_greenhouse_jobs(
    company_name: str,
    board_token: str,
) -> List[Job]:
    url = (
        "https://boards-api.greenhouse.io/v1/"
        f"boards/{board_token}/jobs?content=true"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    results: List[Job] = []

    for item in response.json().get("jobs", []):
        location = item.get("location", {}).get("name", "")

        results.append(
            Job(
                company=company_name,
                title=item.get("title", ""),
                location=location,
                url=item.get("absolute_url", ""),
                source="Greenhouse",
                description=clean_html(item.get("content", "")),
            )
        )

    return results