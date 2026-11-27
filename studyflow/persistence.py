"""Постійність: шляхи даних і версійовані JSON-знімки."""
import json
import os
import sqlite3
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from .core import Task, TaskService


def default_database_path() -> Path:
    """Зберегти доступ до старої бази або обрати каталог користувача."""
    legacy = Path.cwd() / "studyflow.db"
    if legacy.is_file():
        return legacy
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or
                    Path.home() / "AppData" / "Local")
        return base / "StudyFlow" / "studyflow.db"
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "studyflow" / "studyflow.db"


class SnapshotRepository(Protocol):
    path: Path | None
    def all(self) -> list[Task]: ...
    def replace_all(self, tasks: list[Task]) -> None: ...


class JsonSnapshotStore:
    """Data Mapper: Task <-> JSON; відновлення через репозиторій."""
    VERSION = 1

    def __init__(self, repository: SnapshotRepository):
        self.repository = repository

    def _check_path(self, value: str) -> Path:
        path = Path(value).expanduser().resolve()
        database = self.repository.path
        if database is not None:
            reserved = [database, *(Path(str(database) + suffix)
                                     for suffix in ("-wal", "-shm", "-journal"))]
            for item in reserved:
                if path == item or (path.exists() and item.exists()
                                    and path.samefile(item)):
                    raise ValueError("Не можна використовувати файл бази як знімок")
        return path

    def save(self, value: str) -> int:
        path = self._check_path(value)
        tasks = self.repository.all()
        payload = {"version": self.VERSION,
                   "tasks": [asdict(task) for task in tasks]}
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=path.parent,
                    prefix=".studyflow-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return len(tasks)

    @classmethod
    def decode(cls, payload: object) -> list[Task]:
        if (not isinstance(payload, dict)
                or type(payload.get("version")) is not int
                or payload["version"] != cls.VERSION
                or not isinstance(payload.get("tasks"), list)):
            raise ValueError("Невідомий формат або версія знімка")
        tasks = []
        seen = set()
        for row in payload["tasks"]:
            if (not isinstance(row, dict) or
                    set(row) != {"id", "subject", "title", "deadline", "completed"}):
                raise ValueError("Некоректна структура завдання")
            task_id = row["id"]
            if (type(task_id) is not int or not 0 < task_id < 2**63 - 1
                    or task_id in seen):
                raise ValueError("Некоректний або повторний ID")
            if any(not isinstance(row[key], str) or not row[key].strip()
                   for key in ("subject", "title", "deadline")):
                raise ValueError("Некоректні текстові поля")
            if type(row["completed"]) is not bool:
                raise ValueError("Некоректна ознака виконання")
            deadline = TaskService.validate_deadline(row["deadline"])
            tasks.append(Task(task_id, row["subject"].strip(),
                              row["title"].strip(), deadline, row["completed"]))
            seen.add(task_id)
        return tasks

    def load(self, value: str) -> int:
        path = self._check_path(value)
        with path.open("r", encoding="utf-8") as stream:
            tasks = self.decode(json.load(stream))
        # Валідація всього документа відбувається до першої зміни БД.
        try:
            self.repository.replace_all(tasks)
        except sqlite3.DatabaseError as exc:
            raise ValueError("Не вдалося відновити знімок; зміни скасовано") from exc
        return len(tasks)
