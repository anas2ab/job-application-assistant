import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class JobdeskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = patch.multiple(
            server,
            DATA_PATH=self.root / "applications.json",
            PROFILE_PATH=self.root / "profile.json",
            DOCUMENTS_PATH=self.root / "documents.json",
            EXCLUSIONS_PATH=self.root / "exclusions.json",
        )
        self.paths.start()

    def tearDown(self):
        self.paths.stop()
        self.temp.cleanup()

    def test_profile_scoring_rewards_title_skills_and_location(self):
        raw = {
            "title": "Senior Software Engineer",
            "description": "Java Spring Boot Kafka AWS Kubernetes",
            "location": "Example City",
        }
        profile = {**server.DEFAULT_PROFILE, "locations": "Example City, Remote"}
        score, skills = server.profile_score(raw, profile)
        self.assertGreaterEqual(score, 75)
        self.assertIn("Java", skills)
        self.assertIn("Kafka", skills)

    def test_documents_use_saved_profile_and_persist_edits(self):
        profile = {**server.DEFAULT_PROFILE, "name": "Test Candidate", "resume": "Improved API latency by 42%."}
        server.PROFILE_PATH.write_text(server.json.dumps(profile))
        job = {
            "id": "test-job",
            "company": "Real Company",
            "title": "Senior Software Engineer",
            "location": "Example City",
            "salary": "Not listed",
            "skills": ["Java", "Kafka"],
        }
        documents = server.generated_documents(job)
        self.assertIn("Test Candidate", documents["resume_summary"])
        self.assertIn("Improved API latency by 42%.", documents["resume_summary"])
        self.assertTrue(server.DOCUMENTS_PATH.exists())

    def test_new_install_starts_without_placeholder_jobs(self):
        self.assertEqual(server.load_data(), [])

    def test_onsite_jobs_must_be_in_toronto(self):
        eligible, _, _ = server.eligibility({
            "location": "Vancouver, Canada",
            "description": "Work from our office. Annual salary $180,000–$210,000 CAD.",
        })
        self.assertFalse(eligible)
        eligible, _, _ = server.eligibility({
            "location": "Toronto, Canada",
            "description": "Work from our office. Annual salary $180,000–$210,000 CAD.",
        })
        self.assertTrue(eligible)

    def test_remote_jobs_must_allow_canada_or_worldwide(self):
        canada, _, _ = server.eligibility({"location": "Remote - Canada", "description": ""})
        worldwide, _, _ = server.eligibility({"location": "Remote", "description": "Open to candidates worldwide."})
        us_only, _, _ = server.eligibility({"location": "Remote - USA", "description": ""})
        self.assertTrue(canada)
        self.assertTrue(worldwide)
        self.assertFalse(us_only)

    def test_published_salary_minimum_must_exceed_threshold(self):
        below, salary, _ = server.eligibility({
            "location": "Toronto",
            "description": "Annual salary range: $145,000–$190,000 CAD.",
        })
        above, _, _ = server.eligibility({
            "location": "Toronto",
            "description": "Annual salary range: $151,000–$190,000 CAD.",
        })
        unlisted, display, _ = server.eligibility({"location": "Toronto", "description": "Competitive pay."})
        self.assertFalse(below)
        self.assertEqual(salary, "$145,000–$190,000 CAD")
        self.assertTrue(above)
        self.assertTrue(unlisted)
        self.assertEqual(display, "Not listed")

    def test_dismissal_rule_blocks_future_matching_jobs(self):
        job = {
            "company": "Example Company",
            "title": "Backend Engineer",
            "location": "Toronto, Ontario",
            "description": "Java services",
        }
        rule = server.add_exclusion(job, "location")
        self.assertEqual(rule, {"type": "location", "value": "Toronto, Ontario"})
        self.assertEqual(server.exclusion_match(job), "location")
        different_location = {**job, "location": "Remote - Canada"}
        self.assertIsNone(server.exclusion_match(different_location))

    def test_keyword_rule_matches_title_or_description(self):
        job = {
            "company": "Example Company",
            "title": "Backend Engineer",
            "location": "Remote - Canada",
            "description": "Requires regular overnight on-call shifts",
        }
        server.add_exclusion(job, "keyword", "overnight on-call")
        self.assertEqual(server.exclusion_match(job), "keyword")


if __name__ == "__main__":
    unittest.main()
