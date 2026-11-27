"""Перевірки постійності: повторний запуск, JSON і транзакції."""
import json
import tempfile
import unittest
from pathlib import Path

from studyflow.cli import CLI, PersistenceStrategy, TextRenderer
from studyflow.core import Task, TaskService
from studyflow.data import SQLiteRepository
from studyflow.persistence import JsonSnapshotStore


class FakeIO:
    def __init__(self):
        self.output = []

    def write(self, text):
        self.output.append(text)

    def read(self, prompt):
        raise EOFError


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.db = self.root / "data" / "studyflow.db"
        self.repository = SQLiteRepository(str(self.db))
        self.addCleanup(self.repository.close)
        self.service = TaskService(self.repository)
        self.store = JsonSnapshotStore(self.repository)
        self.snapshot = self.root / "резервна копія.json"

    def add(self, title="Практична 15"):
        return self.service.add("Інформатика", title, "2026-12-05 18:00")

    def write_payload(self, payload):
        self.snapshot.write_text(json.dumps(payload), encoding="utf-8")

    def test_database_reopen(self):
        task_id = self.add()
        self.service.done(task_id)
        self.service.edit(task_id, "2026-12-06 18:00")
        second = SQLiteRepository(str(self.db))
        try:
            task = second.all()[0]
            self.assertTrue(task.completed)
            self.assertEqual(task.deadline, "2026-12-06 18:00")
            self.assertEqual(task.id, task_id)
        finally:
            second.close()

    def test_snapshot_round_trip(self):
        first = self.add()
        second = self.add("Інше")
        self.service.done(first)
        self.service.delete(second)
        original = self.repository.all()
        self.assertEqual(self.store.save(str(self.snapshot)), 1)
        self.service.delete(first)
        self.add("Новий запис")
        self.assertEqual(self.store.load(str(self.snapshot)), 1)
        self.assertEqual(self.repository.all(), original)
        self.assertGreater(self.add(), first)

    def test_utf8_and_version(self):
        self.add()
        self.store.save(str(self.snapshot))
        raw = self.snapshot.read_text(encoding="utf-8")
        self.assertIn("Інформатика", raw)
        self.assertEqual(json.loads(raw)["version"], 1)

    def test_empty_snapshot(self):
        self.store.save(str(self.snapshot))
        self.add()
        self.assertEqual(self.store.load(str(self.snapshot)), 0)
        self.assertEqual(self.repository.all(), [])

    def test_invalid_json_preserves_data(self):
        self.add()
        self.snapshot.write_text("{invalid", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.load(str(self.snapshot))
        self.assertEqual(len(self.repository.all()), 1)

    def test_unknown_version_preserves_data(self):
        self.add()
        self.write_payload({"version": 2, "tasks": []})
        with self.assertRaises(ValueError):
            self.store.load(str(self.snapshot))
        self.assertEqual(len(self.repository.all()), 1)

    def test_invalid_second_task_preserves_data(self):
        self.add()
        row = {"id": 5, "subject": "Історія", "title": "Реферат",
               "deadline": "2026-12-05 18:00", "completed": False}
        bad = dict(row, id=6, deadline="2026-02-30 12:00")
        self.write_payload({"version": 1, "tasks": [row, bad]})
        before = self.repository.all()
        with self.assertRaises(ValueError):
            self.store.load(str(self.snapshot))
        self.assertEqual(self.repository.all(), before)

    def test_duplicate_id_rejected(self):
        self.add()
        row = {"id": 1, "subject": "Історія", "title": "Тест",
               "deadline": "2026-12-05 18:00", "completed": False}
        self.write_payload({"version": 1, "tasks": [row, row]})
        with self.assertRaises(ValueError):
            self.store.load(str(self.snapshot))
        self.assertEqual(len(self.repository.all()), 1)

    def test_completed_requires_boolean(self):
        self.write_payload({"version": 1, "tasks": [
            {"id": 1, "subject": "Історія", "title": "Тест",
             "deadline": "2026-12-05 18:00", "completed": "false"}]})
        with self.assertRaises(ValueError):
            self.store.load(str(self.snapshot))

    def test_database_cannot_be_snapshot(self):
        self.add()
        with self.assertRaises(ValueError):
            self.store.save(str(self.db))
        self.assertEqual(len(self.repository.all()), 1)

    def test_repository_rolls_back_on_conflict(self):
        import sqlite3
        self.add()
        before = self.repository.all()
        row = Task(5, "Історія", "Тест", "2026-12-05 18:00")
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.replace_all([row, row])
        self.assertEqual(self.repository.all(), before)

    def test_cli_save_load_and_confirmation(self):
        self.add()
        io = FakeIO()
        cli = CLI(self.service, io, TextRenderer())
        cli.use_strategy(PersistenceStrategy(self.store))
        path = self.snapshot.as_posix()
        cli.exec_command(f'save "{path}"')
        self.assertIn("Збережено", io.output[-1])
        self.add("Новий запис")
        cli.exec_command(f'load "{path}"')
        self.assertIn("Помилка", io.output[-1])
        self.assertEqual(len(self.repository.all()), 2)
        cli.exec_command(f'load "{path}" --replace')
        self.assertIn("Відновлено", io.output[-1])
        self.assertEqual(len(self.repository.all()), 1)

    def test_missing_file_does_not_end_cli(self):
        io = FakeIO()
        cli = CLI(self.service, io, TextRenderer())
        cli.use_strategy(PersistenceStrategy(self.store))
        cli.exec_command(f'load "{self.snapshot.as_posix()}" --replace')
        self.assertIn("Помилка", io.output[-1])
        self.assertTrue(cli.running)


if __name__ == "__main__":
    unittest.main()
