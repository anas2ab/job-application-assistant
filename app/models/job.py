from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Job:
    external_id: str
    company: str
    title: str
    location: str
    url: str
    source: str
    description: str = ""
    department: str = ""
    workplace_type: str = ""
    employment_type: str = ""
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: str = ""
    date_posted: str = ""
    score: int = 0
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)