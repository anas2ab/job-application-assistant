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


if __name__ == "__main__":
    unittest.main()
