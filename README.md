<div align="center">

# Jobdesk

**A private, local-first workspace for managing your entire job search.**

Discover relevant roles, score them against your experience, prepare tailored
application materials, track follow-ups, and measure what is working.

![Python](https://img.shields.io/badge/Python-3.9%2B-3157ED?style=flat-square&logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/runtime_dependencies-none-278663?style=flat-square)
![Data](https://img.shields.io/badge/personal_data-local_only-171916?style=flat-square)

</div>

---

## What Jobdesk does

- Searches configured Greenhouse and Lever company boards for live openings
- Deduplicates results and scores each job against your titles, skills, and locations
- Explains which skills contributed to each match
- Produces editable resume drafts, cover letters, and screening answers
- Opens the employer's official application page
- Tracks roles through review, tailoring, application, and interview stages
- Automatically schedules a seven-day follow-up after an application
- Calculates response rates and interview conversion from your real activity
- Stores all personal data locally on your computer

## Quick start

Jobdesk has no runtime package dependencies. You only need Python 3.9 or newer.

```bash
git clone <your-fork-or-repository-url>
cd job-application-assistant
python server.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

To stop Jobdesk, return to the terminal and press `Control+C`.

## Set up your search

1. Open **Profile**.
2. Paste the text from your current resume.
3. Add your target titles, core skills, preferred locations, work authorization,
   and optional salary expectations.
4. Select **Save profile**.
5. Return to **Discover** and select **Search now**.

New installations begin with an empty job list. Only jobs returned by connected
live sources are added.

## Apply to a job

1. Select a role under **Discover**.
2. Review its score and matching skills.
3. Edit the tailored resume, cover letter, or screening answers.
4. Download your documents as text files.
5. Select **Open application** to visit the employer's official form.
6. After submitting, return to Jobdesk and select **Update status**.

Marking a job as applied records the application date and schedules a follow-up
seven days later.

## Source coverage

| Source | Status | Integration approach |
|---|---:|---|
| Greenhouse | Connected | Public job-board API |
| Lever | Connected | Public postings API |
| Ashby | Planned | Public job-board API |
| SmartRecruiters | Planned | Public jobs API |
| Workday | Planned | Company-specific adapters |
| Company career sites | Planned | Authorized per-site adapters |
| LinkedIn | Planned | Saved-search notifications or approved provider |

LinkedIn, Workday, and many company sites do not provide a universal public jobs
API. Jobdesk intentionally does not bypass authentication, CAPTCHAs, access
controls, or platform terms.

## Privacy

Your personal information is not stored in the repository. Jobdesk creates the
following files locally as you use it:

| Local file | Contents |
|---|---|
| `profile.json` | Resume text, preferences, and screening defaults |
| `applications.json` | Discovered jobs and application status |
| `documents.json` | Generated and edited application materials |
| `job_application_tracker.xlsx` | Optional legacy Excel tracker |

These files, along with resumes, exports, credentials, and environment files,
are excluded by [.gitignore](.gitignore).

> [!IMPORTANT]
> If you previously committed personal data before adding `.gitignore`, ignoring
> the file does not remove it from Git history. Remove it from tracking and audit
> the repository history before publishing.

## Document generation

The default generator is deterministic and grounded in the resume text saved in
your profile. This keeps the app usable without API keys and makes every draft
editable before use.

For higher-quality rewriting, replace `generated_documents()` in `server.py`
with your preferred model provider. Keep human review enabled for every document.
Jobdesk never infers sensitive demographic or legal screening answers.

## Project structure

```text
.
├── server.py                 # Local HTTP server, APIs, sync, and persistence
├── companies.py              # Configured Greenhouse and Lever organizations
├── scorer.py                 # Match scoring logic
├── config.py                 # Default titles, skills, and score settings
├── greenhouse.py             # Standalone Greenhouse collector
├── lever.py                  # Standalone Lever collector
├── find_jobs.py              # Legacy collector-to-Excel workflow
├── web/
│   ├── index.html            # Application interface
│   ├── styles.css            # Responsive visual system
│   └── app.js                # Client-side workflows
└── tests/
    └── test_server.py        # Scoring, persistence, and document tests
```

## Run the tests

```bash
python -m unittest discover -s tests -v
```

## Configuration

Edit [companies.py](companies.py) to change the organizations searched through
Greenhouse and Lever. Adjust [config.py](config.py) if you use the standalone
collector and Excel workflow.

Preferences entered in the web app are saved separately in the ignored local
profile and are used for dashboard scoring.

## Contributing

Contributions are welcome, particularly for:

- Ashby and SmartRecruiters collectors
- Authorized Workday and career-site adapters
- Importing saved searches and job-alert emails
- Optional model-provider integrations
- PDF and DOCX export
- Accessibility and automated browser testing

Please keep integrations compliant with source terms, avoid committing personal
data, and run the test suite before opening a pull request.
