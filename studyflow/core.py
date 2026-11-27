"""Предметна логіка без залежності від консолі."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Protocol

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


class TaskStatus(str, Enum):
    COMPLETED = "Виконано"
    OVERDUE = "Прострочено"
    URGENT = "Терміново"
    UPCOMING = "Заплановано"


class PriorityPolicy(Protocol):
    """Strategy: взаємозамінне правило оцінки терміновості."""
    def classify(self, task: Task, now: datetime) -> TaskStatus: ...


@dataclass(frozen=True)
class DeadlinePolicy:
    urgent_hours: int = 24

    def __post_init__(self) -> None:
        if self.urgent_hours <= 0:
            raise ValueError("Поріг терміновості має бути додатним")

    def classify(self, task: Task, now: datetime) -> TaskStatus:
        if task.completed:
            return TaskStatus.COMPLETED
        remaining = datetime.strptime(task.deadline, DATE_FORMAT) - now
        if remaining.total_seconds() < 0:
            return TaskStatus.OVERDUE
        if remaining <= timedelta(hours=self.urgent_hours):
            return TaskStatus.URGENT
        return TaskStatus.UPCOMING


@dataclass(frozen=True)
class PlannedTask:
    task: Task
    status: TaskStatus


@dataclass(frozen=True)
class ProgressReport:
    total: int
    completed: int
    overdue: int
    urgent: int
    upcoming: int

    @property
    def completion_percent(self) -> float:
        return round(100 * self.completed / self.total, 1) if self.total else 0.0


class TaskService:
    """Facade для предметної логіки; не залежить від CLI або SQLite."""
    def __init__(self, repository: Repository,
                 policy: PriorityPolicy | None = None,
                 clock: Callable[[], datetime] | None = None):
        self.repository = repository
        self.policy = policy if policy is not None else DeadlinePolicy()
        self.clock = clock if clock is not None else datetime.now

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
        today = (now if now is not None else self.clock()).date()
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

    def plan(self, now: datetime | None = None) -> list[PlannedTask]:
        """Активні завдання: прострочені, термінові, заплановані."""
        moment = now if now is not None else self.clock()
        order = {TaskStatus.OVERDUE: 0, TaskStatus.URGENT: 1,
                 TaskStatus.UPCOMING: 2, TaskStatus.COMPLETED: 3}
        planned = [PlannedTask(task, self.policy.classify(task, moment))
                   for task in self.repository.all() if not task.completed]
        return sorted(planned, key=lambda entry: (
            order[entry.status], entry.task.deadline, entry.task.id))

    def overdue(self, now: datetime | None = None) -> list[Task]:
        return [entry.task for entry in self.plan(now)
                if entry.status == TaskStatus.OVERDUE]

    def progress(self, now: datetime | None = None) -> ProgressReport:
        moment = now if now is not None else self.clock()
        tasks = self.repository.all()
        completed = sum(task.completed for task in tasks)
        statuses = [self.policy.classify(task, moment)
                    for task in tasks if not task.completed]
        return ProgressReport(
            total=len(tasks), completed=completed,
            overdue=statuses.count(TaskStatus.OVERDUE),
            urgent=statuses.count(TaskStatus.URGENT),
            upcoming=statuses.count(TaskStatus.UPCOMING))
