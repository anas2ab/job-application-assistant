"""Local web app for the job application assistant.

Run with: python server.py
"""

from __future__ import annotations

import json
import mimetypes
import re
import html
import uuid
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from companies import (
    ASHBY_COMPANIES,
    GREENHOUSE_COMPANIES,
    LEVER_COMPANIES,
    SMARTRECRUITERS_COMPANIES,
    WORKDAY_COMPANIES,
)
from config import MINIMUM_SALARY_CAD, USD_TO_CAD
ROOT = Path(__file__).parent
WEB_ROOT = ROOT / "web"
DATA_PATH = ROOT / "applications.json"
PROFILE_PATH = ROOT / "profile.json"
DOCUMENTS_PATH = ROOT / "documents.json"
EXCLUSIONS_PATH = ROOT / "exclusions.json"
VALID_STATUSES = {"Review", "Tailoring", "Applied", "Interview", "Offer", "Rejected", "No response", "Dismissed"}

DEFAULT_PROFILE = {
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "resume": "",
    "target_titles": "Senior Software Engineer, Backend Software Engineer, Platform Engineer",
    "skills": "Java, Spring Boot, Microservices, Kafka, AWS, Kubernetes, Docker, Python, MongoDB, MySQL, CI/CD",
    "locations": "Remote",
    "work_authorization": "",
    "salary_expectation": "",
}


def seed_data() -> list[dict]:
    return []


def load_data() -> list[dict]:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text())
    return seed_data()


def save_data(data: list[dict]) -> None:
    DATA_PATH.write_text(json.dumps(data, indent=2))


def load_json(path: Path, fallback: object) -> object:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return fallback


def load_profile() -> dict:
    return {**DEFAULT_PROFILE, **load_json(PROFILE_PATH, {})}


def load_exclusions() -> dict:
    defaults = {"locations": [], "companies": [], "titles": [], "keywords": []}
    saved = load_json(EXCLUSIONS_PATH, {})
    return {key: list(saved.get(key, [])) for key in defaults}


def exclusion_match(raw: dict, exclusions: Optional[dict] = None) -> Optional[str]:
    exclusions = exclusions or load_exclusions()
    location = raw.get("location", "").strip().lower()
    company = raw.get("company", "").strip().lower()
    title = raw.get("title", "").strip().lower()
    full_text = f"{title} {raw.get('description', '')}".lower()
    if any(value.lower() == location for value in exclusions["locations"]):
        return "location"
    if any(value.lower() == company for value in exclusions["companies"]):
        return "company"
    if any(value.lower() == title for value in exclusions["titles"]):
        return "title"
    if any(value.lower() in full_text for value in exclusions["keywords"]):
        return "keyword"
    return None


def add_exclusion(job: dict, reason: str, detail: str = "") -> Optional[dict]:
    mapping = {
        "location": ("locations", job.get("location", "")),
        "company": ("companies", job.get("company", "")),
        "title": ("titles", job.get("title", "")),
        "keyword": ("keywords", detail),
    }
    if reason not in mapping:
        return None
    group, value = mapping[reason]
    value = value.strip()
    if not value:
        return None
    exclusions = load_exclusions()
    if value.lower() not in {existing.lower() for existing in exclusions[group]}:
        exclusions[group].append(value)
        EXCLUSIONS_PATH.write_text(json.dumps(exclusions, indent=2))
    return {"type": reason, "value": value}


def clean_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value or ""))).strip()


def extract_salary(text: str, location: str = "") -> Optional[dict]:
    """Extract an annual CAD/USD salary range when a posting publishes one."""
    salary_contexts = re.findall(
        r"(?i)(?:salary|compensation|base pay|pay range|annual base)[^.!?\n]{0,180}",
        text,
    )
    contexts = salary_contexts or [text]
    number = r"(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d+)?\s*[kK])"
    range_pattern = re.compile(
        rf"(?i)(CAD|USD|CA\$|US\$|\$)?\s*{number}\s*(?:-|–|—|to)\s*"
        rf"(CAD|USD|CA\$|US\$|\$)?\s*{number}\s*(CAD|USD)?"
    )
    for context in contexts:
        match = range_pattern.search(context)
        if not match:
            continue

        def amount(value: str) -> int:
            normalized = value.replace(",", "").replace(" ", "")
            return round(float(normalized[:-1]) * 1000) if normalized.lower().endswith("k") else round(float(normalized))

        low, high = amount(match.group(2)), amount(match.group(4))
        if low < 40_000 or high < low:
            continue
        currency_markers = " ".join(filter(None, (match.group(1), match.group(3), match.group(5)))).upper()
        nearby = context.upper()
        if "CAD" in currency_markers or "CA$" in currency_markers or " CAD" in nearby:
            currency = "CAD"
        elif "USD" in currency_markers or "US$" in currency_markers or " USD" in nearby:
            currency = "USD"
        else:
            currency = "CAD" if "canada" in location.lower() or "toronto" in location.lower() else "USD"
        low_cad = round(low * USD_TO_CAD) if currency == "USD" else low
        high_cad = round(high * USD_TO_CAD) if currency == "USD" else high
        return {
            "low": low,
            "high": high,
            "currency": currency,
            "low_cad": low_cad,
            "high_cad": high_cad,
            "display": f"${low:,}–${high:,} {currency}",
        }
    return None


def eligibility(raw: dict) -> tuple[bool, str, str]:
    """Apply the Toronto/remote-Canada and compensation requirements."""
    location = raw.get("location", "")
    description = raw.get("description", "")
    location_text = location.lower()
    full_text = f"{location} {description}".lower()
    is_remote = "remote" in full_text
    is_hybrid = "hybrid" in full_text

    if is_remote:
        worldwide = any(term in full_text for term in ("worldwide", "anywhere", "work from anywhere", "global remote"))
        canada = any(term in full_text for term in ("canada", "canadian"))
        restricted_elsewhere = any(term in location_text for term in (
            "united states", "usa", "u.s.", "uk", "united kingdom", "emea",
            "europe", "australia", "india", "latin america",
        ))
        generic_remote = location_text.strip() in {"remote", "remote work", "fully remote"}
        if not (worldwide or canada or (generic_remote and not restricted_elsewhere)):
            return False, "Not listed", "Remote role is not available in Canada or worldwide"
    elif "toronto" not in full_text:
        return False, "Not listed", "On-site or hybrid role is not based in Toronto"

    salary = extract_salary(description, location)
    if salary and salary["low_cad"] <= MINIMUM_SALARY_CAD:
        return False, salary["display"], f"Published minimum is not above CAD ${MINIMUM_SALARY_CAD:,}"
    return True, salary["display"] if salary else "Not listed", "Eligible"


def fetch_json(url: str) -> object:
    request = Request(url, headers={"User-Agent": "Jobdesk/1.0 (+local job search assistant)"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read())


def fetch_json_post(url: str, payload: dict) -> object:
    body = json.dumps(payload).encode()
    request = Request(
        url,
        data=body,
        headers={"User-Agent": "Jobdesk/1.0 (+local job search assistant)", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=25) as response:
        return json.loads(response.read())


def fetch_source(source: str, company: str, token: object) -> list[dict]:
    if source == "Greenhouse":
        payload = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
        raw_jobs = [{
            "title": item.get("title", ""),
            "location": item.get("location", {}).get("name", ""),
            "url": item.get("absolute_url", ""),
            "description": clean_html(item.get("content", "")),
        } for item in payload.get("jobs", [])]
    elif source == "Lever":
        payload = fetch_json(f"https://api.lever.co/v0/postings/{token}?mode=json")
        raw_jobs = [{
            "title": item.get("text", ""),
            "location": item.get("categories", {}).get("location", ""),
            "url": item.get("hostedUrl", ""),
            "description": clean_html(" ".join([item.get("descriptionPlain", ""), item.get("additionalPlain", "")])),
        } for item in payload]
    elif source == "Ashby":
        payload = fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true")
        raw_jobs = []
        for item in payload.get("jobs", []):
            if not item.get("isListed", True):
                continue
            compensation = item.get("compensation") or {}
            summary = compensation.get("scrapeableCompensationSalarySummary", "")
            currency = ""
            for component in compensation.get("summaryComponents", []):
                if component.get("compensationType") == "Salary":
                    currency = component.get("currencyCode", "")
                    break
            description = item.get("descriptionPlain") or clean_html(item.get("descriptionHtml", ""))
            if summary:
                description += f" Annual salary: {summary} {currency}."
            location = item.get("location", "")
            if item.get("isRemote") and "remote" not in location.lower():
                location = f"Remote - {location}".strip(" -")
            raw_jobs.append({
                "title": item.get("title", ""),
                "location": location,
                "url": item.get("applyUrl") or item.get("jobUrl", ""),
                "description": description,
            })
    elif source == "SmartRecruiters":
        listing = fetch_json(f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100")
        candidates = []
        for item in listing.get("content", []):
            location_data = item.get("location", {})
            location = location_data.get("fullLocation") or ", ".join(filter(None, (
                location_data.get("city"), location_data.get("region"), location_data.get("country"),
            )))
            if location_data.get("remote") and "remote" not in location.lower():
                location = f"Remote - {location}"
            prelim = {"location": location, "description": "", "title": item.get("name", "")}
            if eligibility(prelim)[0]:
                candidates.append((item, location))
        raw_jobs = []
        for item, location in candidates:
            detail = fetch_json(item["ref"])
            sections = detail.get("jobAd", {}).get("sections", {})
            description = clean_html(" ".join(section.get("text", "") for section in sections.values()))
            raw_jobs.append({
                "title": detail.get("name", item.get("name", "")),
                "location": location,
                "url": detail.get("applyUrl") or detail.get("postingUrl", ""),
                "description": description,
            })
    elif source == "Workday":
        host, tenant, site = token["host"], token["tenant"], token["site"]
        base = f"{host}/wday/cxs/{tenant}/{site}"
        postings = []
        for offset in range(0, 200, 20):
            listing = fetch_json_post(f"{base}/jobs", {"appliedFacets": {}, "limit": 20, "offset": offset})
            page = listing.get("jobPostings", [])
            postings.extend(page)
            if len(postings) >= listing.get("total", len(postings)) or len(page) < 20:
                break
        candidates = []
        for item in postings:
            prelim = {
                "title": item.get("title", ""),
                "location": item.get("locationsText", ""),
                "description": "",
            }
            if eligibility(prelim)[0]:
                candidates.append(item)
        raw_jobs = []
        for item in candidates:
            path = item.get("externalPath", "")
            detail = fetch_json(f"{base}{path}")
            info = detail.get("jobPostingInfo", {})
            raw_jobs.append({
                "title": info.get("title", item.get("title", "")),
                "location": info.get("location", item.get("locationsText", "")),
                "url": info.get("externalUrl") or f"{host}/en-US/{site}{path}",
                "description": clean_html(info.get("jobDescription", "")),
            })
    else:
        return []
    return [{**item, "company": company, "source": source} for item in raw_jobs if item["url"]]


def profile_score(raw: dict, profile: dict) -> tuple[int, list[str]]:
    text = f"{raw['title']} {raw['description']}".lower()
    desired_titles = [x.strip().lower() for x in profile["target_titles"].split(",") if x.strip()]
    skills = [x.strip() for x in profile["skills"].split(",") if x.strip()]
    locations = [x.strip().lower() for x in profile["locations"].split(",") if x.strip()]
    matched = [skill for skill in skills if skill.lower() in text]
    title_score = 35 if any(title in raw["title"].lower() or raw["title"].lower() in title for title in desired_titles) else 12
    skill_score = min(50, round(50 * len(matched) / max(1, min(8, len(skills)))))
    location_text = raw["location"].lower()
    location_score = 15 if "remote" in location_text or any(place in location_text for place in locations) else 4
    return min(100, title_score + skill_score + location_score), matched


def sync_jobs(sources: Optional[List[str]] = None) -> dict:
    sources = sources or ["Greenhouse", "Lever", "Ashby", "SmartRecruiters", "Workday"]
    configured = []
    if "Greenhouse" in sources:
        configured.extend(("Greenhouse", company, token) for company, token in GREENHOUSE_COMPANIES.items())
    if "Lever" in sources:
        configured.extend(("Lever", company, token) for company, token in LEVER_COMPANIES.items())
    if "Ashby" in sources:
        configured.extend(("Ashby", company, token) for company, token in ASHBY_COMPANIES.items())
    if "SmartRecruiters" in sources:
        configured.extend(("SmartRecruiters", company, token) for company, token in SMARTRECRUITERS_COMPANIES.items())
    if "Workday" in sources:
        configured.extend(("Workday", company, config) for company, config in WORKDAY_COMPANIES.items())
    found, errors = [], []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_source, *args): args for args in configured}
        for future in as_completed(futures):
            source, company, _ = futures[future]
            try:
                found.extend(future.result())
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"{source}: {company} ({type(exc).__name__})")
    data = load_data()
    existing = {item.get("url", "").lower().rstrip("/") for item in data}
    existing_signatures = {
        (item.get("company", "").lower(), item.get("title", "").lower(), item.get("location", "").lower())
        for item in data
    }
    profile = load_profile()
    exclusions = load_exclusions()
    added = 0
    for raw in found:
        normalized = raw["url"].lower().rstrip("/")
        signature = (raw["company"].lower(), raw["title"].lower(), raw["location"].lower())
        if normalized in existing or signature in existing_signatures:
            continue
        if exclusion_match(raw, exclusions):
            continue
        eligible, salary, _ = eligibility(raw)
        if not eligible:
            continue
        score, skills = profile_score(raw, profile)
        if score < 35:
            continue
        work_type = "Remote" if "remote" in f"{raw['location']} {raw['description']}".lower() else "Hybrid" if "hybrid" in f"{raw['location']} {raw['description']}".lower() else "On-site"
        data.append({
            **raw, "id": f"job-{uuid.uuid4().hex[:10]}", "score": score, "skills": skills,
            "work_type": work_type, "status": "Review", "discovered": date.today().isoformat(),
            "applied": None, "follow_up": None, "salary": salary, "notes": "",
        })
        existing.add(normalized)
        existing_signatures.add(signature)
        added += 1
    data.sort(key=lambda item: (item.get("score", 0), item.get("discovered", "")), reverse=True)
    save_data(data)
    return {"scanned": len(found), "added": added, "errors": errors[:10], "sources": sources}


def generated_documents(job: dict, force: bool = False) -> dict:
    saved = load_json(DOCUMENTS_PATH, {})
    if not force and job["id"] in saved:
        return saved[job["id"]]
    profile = load_profile()
    skills = ", ".join(job["skills"][:5])
    company = job["company"]
    title = job["title"]
    resume_body = profile["resume"].strip()
    recent_experience = resume_body[:700] if resume_body else (
        "Experienced backend engineer delivering observable, production-ready distributed services "
        "and partnering with engineering and product teams."
    )
    documents = {
        "resume_summary": (
            f"{profile['name']} — {title}\n{profile['location']} · {profile['email']} · {profile['phone']}\n\n"
            f"PROFESSIONAL SUMMARY\nBackend software engineer experienced in delivering resilient, distributed systems with {skills}. "
            f"Proven track record translating product needs into observable, production-ready services—aligned "
            f"with the {title} role at {company}.\n\nSELECTED EXPERIENCE\n{recent_experience}\n\nCORE SKILLS\n{profile['skills']}"
        ),
        "cover_letter": (
            f"Dear {company} hiring team,\n\n"
            f"I’m excited to apply for the {title} role. The opportunity to work on systems using {skills} "
            "strongly matches the platforms I have built and operated. In my recent work, I improved service "
            "reliability, shortened delivery cycles, and partnered across engineering and product to ship "
            "customer-facing capabilities.\n\n"
            f"I would welcome the chance to bring that combination of backend depth and pragmatic execution "
            f"to {company}.\n\nBest,\n{profile['name']}"
        ),
        "answers": [
            {"question": "Why are you interested in this role?", "answer": f"The role combines my backend systems experience with {company}’s product mission and gives me the opportunity to contribute with {skills} from day one."},
            {"question": "What is your work authorization?", "answer": profile["work_authorization"] or "Review and answer manually."},
            {"question": "What are your salary expectations?", "answer": profile["salary_expectation"] or f"I’m targeting the market range for this level. The listed {job['salary']} range is aligned, depending on the full compensation package and role scope."},
        ],
    }
    saved[job["id"]] = documents
    DOCUMENTS_PATH.write_text(json.dumps(saved, indent=2))
    return documents


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        clean = urlparse(path).path.lstrip("/") or "index.html"
        return str(WEB_ROOT / clean)

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs":
            self.send_json(load_data())
            return
        if parsed.path == "/api/profile":
            self.send_json(load_profile())
            return
        if parsed.path == "/api/exclusions":
            self.send_json(load_exclusions())
            return
        if parsed.path == "/api/analytics":
            data = load_data()
            applied = [j for j in data if j.get("status") in {"Applied", "Interview", "Offer", "Rejected", "No response"}]
            responses = [j for j in applied if j.get("status") in {"Interview", "Offer", "Rejected"}]
            interviews = [j for j in applied if j.get("status") in {"Interview", "Offer"}]
            by_source = {}
            for job in applied:
                group = by_source.setdefault(job["source"], {"applications": 0, "responses": 0})
                group["applications"] += 1
                group["responses"] += int(job.get("status") in {"Interview", "Offer", "Rejected"})
            self.send_json({"discovered": len(data), "applied": len(applied), "responses": len(responses), "interviews": len(interviews), "by_source": by_source})
            return
        if match := re.fullmatch(r"/api/jobs/([^/]+)/documents", parsed.path):
            job = next((item for item in load_data() if item["id"] == match.group(1)), None)
            self.send_json(generated_documents(job) if job else {"error": "Not found"}, 200 if job else 404)
            return
        if match := re.fullmatch(r"/api/jobs/([^/]+)/documents/(resume|cover-letter)\.txt", parsed.path):
            job = next((item for item in load_data() if item["id"] == match.group(1)), None)
            if not job:
                self.send_json({"error": "Not found"}, 404)
                return
            docs = generated_documents(job)
            key = "resume_summary" if match.group(2) == "resume" else "cover_letter"
            body = docs[key].encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{job["company"].replace(" ", "_")}_{match.group(2)}.txt"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if parsed.path == "/api/sync":
            self.send_json(sync_jobs(payload.get("sources")))
            return
        if parsed.path == "/api/profile":
            profile = {**load_profile(), **{key: str(value)[:20000] for key, value in payload.items() if key in DEFAULT_PROFILE}}
            PROFILE_PATH.write_text(json.dumps(profile, indent=2))
            self.send_json(profile)
            return
        if match := re.fullmatch(r"/api/jobs/([^/]+)/dismiss", parsed.path):
            data = load_data()
            job = next((item for item in data if item["id"] == match.group(1)), None)
            if not job:
                self.send_json({"error": "Not found"}, 404)
                return
            reason = str(payload.get("reason", "other")).lower()
            detail = str(payload.get("detail", ""))[:300].strip()
            job["status"] = "Dismissed"
            job["dismissed_at"] = date.today().isoformat()
            job["dismissal_reason"] = reason
            job["dismissal_detail"] = detail
            rule = add_exclusion(job, reason, detail)
            save_data(data)
            self.send_json({"job": job, "rule": rule})
            return
        if match := re.fullmatch(r"/api/jobs/([^/]+)/documents", parsed.path):
            data = load_json(DOCUMENTS_PATH, {})
            current = data.get(match.group(1), {})
            for key in ("resume_summary", "cover_letter", "answers"):
                if key in payload:
                    current[key] = payload[key]
            data[match.group(1)] = current
            DOCUMENTS_PATH.write_text(json.dumps(data, indent=2))
            self.send_json(current)
            return
        self.send_json({"error": "Not found"}, 404)

    def do_PATCH(self) -> None:
        match = re.fullmatch(r"/api/jobs/([^/]+)", urlparse(self.path).path)
        if not match:
            self.send_json({"error": "Not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", 0))
        changes = json.loads(self.rfile.read(length) or b"{}")
        data = load_data()
        job = next((item for item in data if item["id"] == match.group(1)), None)
        if not job:
            self.send_json({"error": "Not found"}, 404)
            return
        allowed = {"follow_up", "notes"}
        job.update({key: value for key, value in changes.items() if key in allowed})
        requested_status = changes.get("status")
        if requested_status in VALID_STATUSES:
            job["status"] = requested_status
        if changes.get("status") == "Applied" and not job.get("applied"):
            job["applied"] = date.today().isoformat()
            job["follow_up"] = (date.today() + timedelta(days=7)).isoformat()
        elif requested_status in {"Interview", "Offer", "Rejected", "No response"}:
            job["follow_up"] = None
        save_data(data)
        self.send_json(job)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[jobdesk] {format % args}")


class JobdeskServer(ThreadingHTTPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    mimetypes.add_type("text/javascript", ".js")
    print("Jobdesk is running at http://127.0.0.1:8000")
    JobdeskServer(("127.0.0.1", 8000), Handler).serve_forever()
