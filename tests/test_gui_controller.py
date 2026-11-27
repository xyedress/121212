"""Тести контролера GUI без потреби у графічному дисплеї."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from studyflow.core import TaskService
from studyflow.data import SQLiteRepository
from studyflow.gui_controller import PlannerController
from studyflow.persistence import JsonSnapshotStore


class GuiControllerTests(unittest.TestCase):
    def setUp(self):
        self.repo = SQLiteRepository(":memory:")
        self.addCleanup(self.repo.close)
        self.now = datetime(2026, 12, 1, 12)
        self.controller = PlannerController(
            TaskService(self.repo, clock=lambda: self.now),
            JsonSnapshotStore(self.repo))

    def add(self, title="Практична 16", deadline="2026-12-02 12:00"):
        return self.controller.add("Інформатика", title, deadline)

    def test_add_and_status(self):
        task_id = self.add()
        row = self.controller.dashboard().rows[0]
        self.assertEqual((row.id, row.title, row.status),
                         (task_id, "Практична 16", "Терміново"))

    def test_search_casefold(self):
        self.add()
        self.add("Реферат")
        self.assertEqual(len(self.controller.dashboard(search="ПРАКТИЧНА").rows), 1)

    def test_mode_filter(self):
        task_id = self.add()
        self.controller.complete(task_id)
        self.assertEqual(self.controller.dashboard(mode="active").rows, ())
        self.assertEqual(self.controller.dashboard(mode="completed").rows[0].id, task_id)

    def test_period_filter(self):
        self.add(deadline="2026-12-01 12:00")
        self.add(deadline="2026-12-20 12:00")
        self.assertEqual(len(self.controller.dashboard(period="today").rows), 1)
        self.assertEqual(len(self.controller.dashboard(period="week").rows), 1)

    def test_progress_global_despite_filter(self):
        task_id = self.add()
        self.add("Інше")
        self.controller.complete(task_id)
        dashboard = self.controller.dashboard(mode="active", search="неіснуюче")
        self.assertEqual(dashboard.rows, ())
        self.assertEqual(dashboard.progress.completion_percent, 50.0)

    def test_edit_deadline(self):
        task_id = self.add()
        self.controller.edit_deadline(task_id, "2026-11-30 12:00")
        self.assertEqual(self.controller.dashboard().rows[0].status, "Прострочено")

    def test_delete(self):
        task_id = self.add()
        self.controller.delete(task_id)
        self.assertEqual(self.controller.dashboard().rows, ())

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            self.controller.add("", "Тест", "2026-12-01 12:00")
        with self.assertRaises(ValueError):
            self.add(deadline="не дата")

    def test_backup_restore(self):
        task_id = self.add()
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "backup.json")
            self.assertEqual(self.controller.save(path), 1)
            self.controller.delete(task_id)
            self.assertEqual(self.controller.load(path, confirmed=True), 1)
            self.assertEqual(self.controller.dashboard().rows[0].id, task_id)

    def test_restore_requires_confirmation(self):
        self.add()
        with self.assertRaises(ValueError):
            self.controller.load("missing.json")
        self.assertEqual(len(self.controller.dashboard().rows), 1)


if __name__ == "__main__":
    unittest.main()
