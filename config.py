TARGET_TITLES = [
    "senior software engineer",
    "software engineer",
    "backend software engineer",
    "java software engineer",
    "platform engineer",
    "senior software developer",
]

REQUIRED_KEYWORDS = [
    "java",
    "spring",
    "spring boot",
    "microservices",
    "kafka",
    "aws",
    "kubernetes",
]

BONUS_KEYWORDS = [
    "docker",
    "openshift",
    "jenkins",
    "ci/cd",
    "event-driven",
    "mongodb",
    "mysql",
    "python",
]

EXCLUDED_KEYWORDS = [
    "principal",
    "staff engineer",
    "director",
    "manager",
    "intern",
    "internship",
    "unpaid",
]

PREFERRED_LOCATIONS = [
    "remote",
]

MINIMUM_SCORE = 65

# Hard eligibility rules used by the web application.
MINIMUM_SALARY_CAD = 150_000

# Used only when a posting publishes USD compensation. Keep this configurable
# because exchange rates change over time.
USD_TO_CAD = 1.35

TRACKER_PATH = "job_application_tracker.xlsx"
