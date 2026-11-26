"""Модульні тести бізнес-логіки без залежності від консолі."""
import unittest
from datetime import datetime
from studyflow.core import (DeadlinePolicy, Task, TaskService, TaskStatus)
from studyflow.data import SQLiteRepository


class MemoryRepository:
    """Fake для незалежної перевірки ядра."""
    def __init__(self):
        self.tasks = []
        self.next_id = 1

    def add(self, subject, title, deadline):
        task_id = self.next_id
        self.next_id += 1
        self.tasks.append(Task(task_id, subject, title, deadline))
        return task_id

    def all(self):
        return list(self.tasks)

    def complete(self, task_id):
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks[i] = Task(task.id, task.subject, task.title,
                                     task.deadline, True)
                return True
        return False

    def edit(self, task_id, deadline):
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks[i] = Task(task.id, task.subject, task.title,
                                     deadline, task.completed)
                return True
        return False

    def delete(self, task_id):
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.id != task_id]
        return len(self.tasks) < before


class BusinessLogicTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 12, 1, 12)
        self.service = TaskService(MemoryRepository(), clock=lambda: self.now)

    def add(self, date, title="Завдання"):
        return self.service.add("Математика", title, date)

    def test_overdue(self):
        self.add("2026-12-01 11:59")
        self.assertEqual(self.service.plan()[0].status, TaskStatus.OVERDUE)

    def test_exact_deadline_is_urgent(self):
        self.add("2026-12-01 12:00")
        self.assertEqual(self.service.plan()[0].status, TaskStatus.URGENT)

    def test_exact_24h_is_urgent(self):
        self.add("2026-12-02 12:00")
        self.assertEqual(self.service.plan()[0].status, TaskStatus.URGENT)

    def test_after_24h_is_upcoming(self):
        self.add("2026-12-02 12:01")
        self.assertEqual(self.service.plan()[0].status, TaskStatus.UPCOMING)

    def test_completed_not_overdue(self):
        task_id = self.add("2026-11-30 10:00")
        self.service.done(task_id)
        self.assertEqual(self.service.overdue(), [])
        self.assertEqual(self.service.plan(), [])
        self.assertEqual(self.service.progress().completion_percent, 100.0)

    def test_plan_sort_and_tie(self):
        later = self.add("2026-12-04 12:00")
        first = self.add("2026-11-30 10:00")
        second = self.add("2026-11-30 10:00")
        urgent = self.add("2026-12-01 13:00")
        self.assertEqual([p.task.id for p in self.service.plan()],
                         [first, second, urgent, later])

    def test_progress_empty(self):
        self.assertEqual(self.service.progress().completion_percent, 0.0)

    def test_progress_groups(self):
        completed = self.add("2026-11-29 12:00")
        self.service.done(completed)
        self.add("2026-11-30 12:00")
        self.add("2026-12-02 12:00")
        self.add("2026-12-03 12:00")
        report = self.service.progress()
        self.assertEqual((report.total, report.completed, report.overdue,
                          report.urgent, report.upcoming), (4, 1, 1, 1, 1))
        self.assertEqual(report.completion_percent, 25.0)

    def test_edit_recalculates_priority(self):
        task_id = self.add("2026-11-30 12:00")
        self.service.edit(task_id, "2026-12-05 12:00")
        self.assertEqual(self.service.plan()[0].status, TaskStatus.UPCOMING)

    def test_policy_replacement(self):
        self.add("2026-12-03 00:00")
        self.assertEqual(self.service.plan()[0].status, TaskStatus.UPCOMING)
        self.service.policy = DeadlinePolicy(48)
        self.assertEqual(self.service.plan()[0].status, TaskStatus.URGENT)

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            DeadlinePolicy(0)

    def test_validation(self):
        with self.assertRaises(ValueError):
            self.service.add(" ", "Назва", "2026-12-01 12:00")
        with self.assertRaises(ValueError):
            self.add("2026-02-30 12:00")

    def test_trim_and_delete(self):
        task_id = self.service.add(" Математика ", " Тест ", "2026-12-01 12:00")
        self.assertEqual(self.service.list()[0].subject, "Математика")
        self.service.delete(task_id)
        self.assertEqual(self.service.progress().total, 0)

    def test_clock_used_for_today(self):
        self.add("2026-12-01 11:00")
        self.add("2026-12-02 11:00")
        self.assertEqual(len(self.service.list(period="today")), 1)

    def test_sqlite_contract(self):
        repository = SQLiteRepository(":memory:")
        self.addCleanup(repository.close)
        service = TaskService(repository, clock=lambda: self.now)
        task_id = service.add("Історія", "Тест", "2026-11-30 12:00")
        self.assertEqual(service.overdue()[0].id, task_id)
        service.done(task_id)
        self.assertEqual(service.progress().completion_percent, 100.0)


if __name__ == "__main__":
    unittest.main()
