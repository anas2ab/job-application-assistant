import logging
from typing import List

from companies import GREENHOUSE_COMPANIES, LEVER_COMPANIES
from config import MINIMUM_SCORE
from excel_tracker import add_jobs
from greenhouse import fetch_greenhouse_jobs
from lever import fetch_lever_jobs
from models import Job
from scorer import score_job


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)


def collect_jobs() -> List[Job]:
    all_jobs: List[Job] = []

    for company_name, token in GREENHOUSE_COMPANIES.items():
        try:
            jobs = fetch_greenhouse_jobs(company_name, token)
            all_jobs.extend(jobs)
            logging.info(
                "Greenhouse: found %s jobs at %s",
                len(jobs),
                company_name,
            )
        except Exception as exc:
            logging.error(
                "Greenhouse failed for %s: %s",
                company_name,
                exc,
            )

    for company_name, token in LEVER_COMPANIES.items():
        try:
            jobs = fetch_lever_jobs(company_name, token)
            all_jobs.extend(jobs)
            logging.info(
                "Lever: found %s jobs at %s",
                len(jobs),
                company_name,
            )
        except Exception as exc:
            logging.error(
                "Lever failed for %s: %s",
                company_name,
                exc,
            )

    return all_jobs


def main() -> None:
    jobs = collect_jobs()

    qualified_jobs = []

    for job in jobs:
        score_job(job)

        if job.score >= MINIMUM_SCORE:
            qualified_jobs.append(job)

    qualified_jobs.sort(
        key=lambda current_job: current_job.score,
        reverse=True,
    )

    added = add_jobs(qualified_jobs)

    print()
    print(f"Collected: {len(jobs)}")
    print(f"Qualified: {len(qualified_jobs)}")
    print(f"Added to Excel: {added}")


if __name__ == "__main__":
    main()