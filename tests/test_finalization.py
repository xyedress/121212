"""Регресійні перевірки фінальної версії."""
import unittest
from studyflow.core import TaskService
from studyflow.data import SQLiteRepository


class FinalizationTests(unittest.TestCase):
    def setUp(self):
        self.repo = SQLiteRepository(":memory:")
        self.addCleanup(self.repo.close)
        self.service = TaskService(self.repo)

    def test_invalid_ids_do_not_reach_sqlite(self):
        task_id = self.service.add("Інформатика", "Тест", "2026-12-05 18:00")
        for invalid in (0, -1, 2**63, 10**100, True):
            with self.subTest(id=invalid):
                with self.assertRaises(ValueError):
                    self.service.done(invalid)
                with self.assertRaises(ValueError):
                    self.service.edit(invalid, "2026-12-06 18:00")
                with self.assertRaises(ValueError):
                    self.service.delete(invalid)
        self.assertEqual(self.service.list()[0].id, task_id)
        self.assertFalse(self.service.list()[0].completed)


if __name__ == "__main__":
    unittest.main()
