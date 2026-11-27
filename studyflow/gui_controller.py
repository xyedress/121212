"""Контролер графічного інтерфейсу, незалежний від Tk."""
from dataclasses import dataclass
from typing import Protocol

from .core import ProgressReport, TaskService


class SnapshotStore(Protocol):
    def save(self, path: str) -> int: ...
    def load(self, path: str) -> int: ...


@dataclass(frozen=True)
class TaskRow:
    id: int
    subject: str
    title: str
    deadline: str
    status: str


@dataclass(frozen=True)
class Dashboard:
    rows: tuple[TaskRow, ...]
    progress: ProgressReport


class PlannerController:
    """MVC: керує сценаріями GUI через готові сервіси."""

    def __init__(self, service: TaskService, snapshots: SnapshotStore):
        self.service = service
        self.snapshots = snapshots

    def dashboard(self, mode="all", period="all", search="") -> Dashboard:
        now = self.service.clock()
        tasks = self.service.list(mode, period, now)
        query = search.strip().casefold()
        rows = tuple(
            TaskRow(task.id, task.subject, task.title, task.deadline,
                    self.service.policy.classify(task, now).value)
            for task in tasks
            if query in f"{task.subject} {task.title}".casefold()
        )
        return Dashboard(rows, self.service.progress(now))

    def add(self, subject: str, title: str, deadline: str) -> int:
        return self.service.add(subject, title, deadline)

    def complete(self, task_id: int) -> None:
        self.service.done(task_id)

    def edit_deadline(self, task_id: int, deadline: str) -> None:
        self.service.edit(task_id, deadline)

    def delete(self, task_id: int) -> None:
        self.service.delete(task_id)

    def save(self, path: str) -> int:
        return self.snapshots.save(path)

    def load(self, path: str, *, confirmed: bool = False) -> int:
        if not confirmed:
            raise ValueError("Потрібне підтвердження заміни поточних даних")
        return self.snapshots.load(path)
