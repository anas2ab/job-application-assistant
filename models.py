from dataclasses import dataclass


@dataclass
class Job:
    company: str
    title: str
    location: str
    url: str
    source: str
    description: str = ""
    work_type: str = ""
    score: int = 0