import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from studyflow.cli import (CLI, ArgsParser, TextRenderer, QueryStrategy,
                           ActionStrategy, SystemStrategy, Command)
from studyflow.core import TaskService
from studyflow.data import SQLiteRepository


class FakeIO:
    def __init__(self, inputs=()):
        self.inputs = iter(inputs)
        self.output = []

    def read(self, prompt):
        return next(self.inputs)

    def write(self, text):
        self.output.append(text)


class StudyFlowTests(unittest.TestCase):
    def setUp(self):
        self.repo = SQLiteRepository(":memory:")
        self.addCleanup(self.repo.close)
        self.service = TaskService(self.repo)
        self.io = FakeIO()
        self.cli = CLI(self.service, self.io, TextRenderer())
        for strategy in (QueryStrategy(), ActionStrategy(), SystemStrategy()):
            self.cli.use_strategy(strategy)

    def add(self):
        self.cli.exec_command('add "Математика" "Практична 5" "2026-12-05 18:00"')

    def test_parser(self):
        args = ArgsParser().parse('add "Два слова" x')
        self.assertEqual(args.values, ("Два слова", "x"))

    def test_add_and_list(self):
        self.add()
        self.cli.exec_command("list")
        self.assertIn("Практична 5", self.io.output[-1])

    def test_done_and_mode(self):
        self.add()
        self.cli.exec_command("done 1")
        self.cli.exec_command("mode active")
        self.cli.exec_command("list")
        self.assertEqual(self.io.output[-1], "Завдань немає.")
        self.cli.exec_command("mode completed")
        self.cli.exec_command("list")
        self.assertIn("Виконано", self.io.output[-1])

    def test_edit_and_delete(self):
        self.add()
        self.cli.exec_command('edit 1 "2026-12-06 10:00"')
        self.assertEqual(self.service.list()[0].deadline, "2026-12-06 10:00")
        self.cli.exec_command("delete 1")
        self.assertEqual(self.service.list(), [])

    def test_invalid_date(self):
        self.cli.exec_command('add x y wrong')
        self.assertIn("Помилка", self.io.output[-1])
        self.assertEqual(self.service.list(), [])

    def test_unknown_command(self):
        self.cli.exec_command("unknown")
        self.assertIn("Помилка", self.io.output[-1])
        self.assertTrue(self.cli.running)

    def test_missing_id(self):
        self.cli.exec_command("done 100")
        self.assertIn("не знайдено", self.io.output[-1])

    def test_periods(self):
        self.add()
        now = datetime(2026, 12, 5, 9)
        self.assertEqual(len(self.service.list(period="today", now=now)), 1)
        self.assertEqual(len(self.service.list(period="week", now=now)), 1)
        self.assertEqual(self.service.list(period="today",
                                           now=datetime(2026, 12, 6)), [])

    def test_dialog(self):
        self.cli.io = FakeIO(["Історія", "Реферат", "2026-12-07 12:00"])
        self.cli.exec_command("add")
        self.assertEqual(self.service.list()[0].title, "Реферат")

    def test_stats_and_exit(self):
        self.add()
        self.cli.exec_command("stats")
        self.assertIn("Активні: 1", self.io.output[-1])
        self.cli.exec_command("exit")
        self.assertFalse(self.cli.running)

    def test_extension(self):
        class Extra:
            def commands(self):
                return [Command("ping", "ping", lambda cli, args: cli.display("pong"))]
        self.cli.use_strategy(Extra())
        self.cli.exec_command("ping")
        self.assertEqual(self.io.output[-1], "pong")

    def test_duplicate_strategy(self):
        with self.assertRaises(ValueError):
            self.cli.use_strategy(QueryStrategy())

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "test.db")
            first = SQLiteRepository(path)
            try:
                TaskService(first).add("Історія", "Тест", "2026-12-05 12:00")
            finally:
                first.close()
            second = SQLiteRepository(path)
            try:
                self.assertEqual(TaskService(second).list()[0].title, "Тест")
            finally:
                second.close()


if __name__ == "__main__":
    unittest.main()
