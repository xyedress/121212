"""Предметна логіка без залежності від консолі."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

DATE_FORMAT = "%Y-%m-%d %H:%M"


@dataclass(frozen=True)
class Task:
    id: int
    subject: str
    title: str
    deadline: str
    completed: bool = False


class Repository(Protocol):
    def add(self, subject: str, title: str, deadline: str) -> int: ...
    def all(self) -> list[Task]: ...
    def complete(self, task_id: int) -> bool: ...
    def edit(self, task_id: int, deadline: str) -> bool: ...
    def delete(self, task_id: int) -> bool: ...


class TaskService:
    def __init__(self, repository: Repository):
        self.repository = repository

    @staticmethod
    def validate_deadline(value: str) -> str:
        try:
            return datetime.strptime(value, DATE_FORMAT).strftime(DATE_FORMAT)
        except ValueError as exc:
            raise ValueError("Дата має формат YYYY-MM-DD HH:MM") from exc

    def add(self, subject: str, title: str, deadline: str) -> int:
        if not subject.strip() or not title.strip():
            raise ValueError("Предмет і назва не можуть бути порожніми")
        return self.repository.add(subject.strip(), title.strip(),
                                   self.validate_deadline(deadline))

    def list(self, mode: str = "all", period: str = "all",
             now: datetime | None = None) -> list[Task]:
        if mode not in ("all", "active", "completed"):
            raise ValueError("Невідомий режим")
        if period not in ("all", "today", "week"):
            raise ValueError("Невідомий період")
        today = (now or datetime.now()).date()
        result = []
        for task in self.repository.all():
            if mode == "active" and task.completed:
                continue
            if mode == "completed" and not task.completed:
                continue
            day = datetime.strptime(task.deadline, DATE_FORMAT).date()
            if period == "today" and day != today:
                continue
            if period == "week" and not today <= day < today + timedelta(days=7):
                continue
            result.append(task)
        return sorted(result, key=lambda t: (t.deadline, t.id))

    def done(self, task_id: int) -> None:
        if not self.repository.complete(task_id):
            raise ValueError("Завдання не знайдено")

    def edit(self, task_id: int, deadline: str) -> None:
        if not self.repository.edit(task_id, self.validate_deadline(deadline)):
            raise ValueError("Завдання не знайдено")

    def delete(self, task_id: int) -> None:
        if not self.repository.delete(task_id):
            raise ValueError("Завдання не знайдено")

    def stats(self) -> dict[str, int]:
        tasks = self.repository.all()
        completed = sum(t.completed for t in tasks)
        return {"Усього": len(tasks), "Виконано": completed,
                "Активні": len(tasks) - completed}
