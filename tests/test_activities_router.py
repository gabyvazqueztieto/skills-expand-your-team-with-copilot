import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backend import database
from src.backend.routers import activities


class FakeActivitiesCollection:
    def __init__(self, documents):
        self._documents = documents
        self.last_query = None

    def find(self, query):
        self.last_query = query
        results = []

        for document in self._documents:
            if "$or" in query:
                if "difficulty" in document and document["difficulty"] is not None:
                    continue
            elif "difficulty" in query and document.get("difficulty") != query["difficulty"]:
                continue

            results.append(document.copy())

        return results


class FakeDatabaseCollection:
    def __init__(self, count):
        self.count = count
        self.updated = []

    def count_documents(self, _query):
        return self.count

    def update_one(self, query, update):
        self.updated.append((query, update))

    def insert_one(self, _document):
        raise AssertionError("insert_one should not be called in this test")


class GetActivitiesDifficultyTests(unittest.TestCase):
    def setUp(self):
        self.documents = [
            {
                "_id": "Programming Class",
                "description": "Learn programming fundamentals",
                "difficulty": "Beginner",
                "participants": [],
                "max_participants": 20,
            },
            {
                "_id": "Science Olympiad",
                "description": "Prepare for science competitions",
                "difficulty": "Advanced",
                "participants": [],
                "max_participants": 18,
            },
            {
                "_id": "Chess Club",
                "description": "Play chess with classmates",
                "participants": [],
                "max_participants": 12,
            },
            {
                "_id": "Art Club",
                "description": "Make art together",
                "difficulty": None,
                "participants": [],
                "max_participants": 15,
            },
        ]

    def test_get_activities_returns_all_when_no_difficulty_filter_is_set(self):
        fake_collection = FakeActivitiesCollection(self.documents)

        with patch.object(activities, "activities_collection", fake_collection):
            result = activities.get_activities()

        self.assertEqual(fake_collection.last_query, {})
        self.assertEqual(set(result.keys()), {"Programming Class", "Science Olympiad", "Chess Club", "Art Club"})
        self.assertEqual(result["Programming Class"]["difficulty"], "Beginner")
        self.assertNotIn("difficulty", result["Chess Club"])

    def test_get_activities_filters_named_difficulty_levels(self):
        fake_collection = FakeActivitiesCollection(self.documents)

        with patch.object(activities, "activities_collection", fake_collection):
            result = activities.get_activities(difficulty="Advanced")

        self.assertEqual(fake_collection.last_query, {"difficulty": "Advanced"})
        self.assertEqual(list(result.keys()), ["Science Olympiad"])

    def test_get_activities_filters_all_levels_activities(self):
        fake_collection = FakeActivitiesCollection(self.documents)

        with patch.object(activities, "activities_collection", fake_collection):
            result = activities.get_activities(difficulty="All")

        self.assertEqual(
            fake_collection.last_query,
            {
                "$or": [
                    {"difficulty": {"$exists": False}},
                    {"difficulty": None},
                ]
            },
        )
        self.assertEqual(set(result.keys()), {"Chess Club", "Art Club"})


class InitDatabaseDifficultyTests(unittest.TestCase):
    def test_init_database_backfills_missing_sample_difficulties(self):
        fake_activities = FakeDatabaseCollection(count=1)
        fake_teachers = FakeDatabaseCollection(count=1)

        with (
            patch.object(database, "activities_collection", fake_activities),
            patch.object(database, "teachers_collection", fake_teachers),
        ):
            database.init_database()

        difficulty_count = sum(
            1 for details in database.initial_activities.values() if "difficulty" in details
        )
        self.assertEqual(len(fake_activities.updated), difficulty_count)
        self.assertEqual(fake_teachers.updated, [])


if __name__ == "__main__":
    unittest.main()
