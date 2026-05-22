import tempfile
import unittest
from pathlib import Path

from app import NotFoundError, RotaRepository, ValidationError


class RotaRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test-rota.db"
        self.repo = RotaRepository(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_list_people(self):
        person = self.repo.create_person("Alice")
        self.assertEqual(person["name"], "Alice")
        people = self.repo.list_people()
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0]["name"], "Alice")
        self.assertEqual(people[0]["active"], 1)

    def test_create_sunday_rejects_non_sunday(self):
        with self.assertRaises(ValidationError):
            self.repo.create_sunday("2026-05-25")

    def test_assignments_persist_and_allow_empty_slots(self):
        alice = self.repo.create_person("Alice")
        bob = self.repo.create_person("Bob")
        sunday = self.repo.create_sunday("2026-05-24")

        updated = self.repo.replace_assignments(
            sunday["id"],
            {
                "assignments": {
                    "band": [alice["id"], bob["id"], None, None],
                    "av": [None, None],
                    "teaCoffee": [None, None],
                    "youth": [None, None],
                    "childrensChurch": [None, None],
                    "welcomers": [None, None],
                }
            },
        )

        band = next(role for role in updated["roles"] if role["key"] == "band")
        self.assertEqual(band["assignments"][0]["personName"], "Alice")
        self.assertEqual(band["assignments"][1]["personName"], "Bob")
        self.assertIsNone(band["assignments"][2]["personId"])

    def test_duplicate_assignments_are_rejected(self):
        alice = self.repo.create_person("Alice")
        sunday = self.repo.create_sunday("2026-05-24")

        with self.assertRaises(ValidationError) as context:
            self.repo.replace_assignments(
                sunday["id"],
                {
                    "assignments": {
                        "band": [alice["id"], None, None, None],
                        "av": [alice["id"], None],
                        "teaCoffee": [None, None],
                        "youth": [None, None],
                        "childrensChurch": [None, None],
                        "welcomers": [None, None],
                    }
                },
            )

        self.assertIn("Alice", str(context.exception))

    def test_inactive_people_cannot_be_assigned(self):
        alice = self.repo.create_person("Alice")
        sunday = self.repo.create_sunday("2026-05-24")
        self.repo.update_person(alice["id"], {"active": False})

        with self.assertRaises(ValidationError):
            self.repo.replace_assignments(
                sunday["id"],
                {
                    "assignments": {
                        "band": [alice["id"], None, None, None],
                        "av": [None, None],
                        "teaCoffee": [None, None],
                        "youth": [None, None],
                        "childrensChurch": [None, None],
                        "welcomers": [None, None],
                    }
                },
            )

    def test_delete_sunday_removes_rota(self):
        sunday = self.repo.create_sunday("2026-05-24")
        self.repo.delete_sunday(sunday["id"])

        with self.assertRaises(NotFoundError):
            self.repo.get_rota(sunday["id"])


if __name__ == "__main__":
    unittest.main()
