"""SQLite-реалізація репозиторію."""
import sqlite3
from pathlib import Path
from .core import Task


class SQLiteRepository:
    def __init__(self, path: str):
        self.path = Path(path).resolve() if path != ':memory:' else None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path if self.path is None else self.path)
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               subject TEXT NOT NULL, title TEXT NOT NULL,
               deadline TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0
               )"""
        )
        self.connection.execute(
            'CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline)')
        self.connection.commit()

    def add(self, subject: str, title: str, deadline: str) -> int:
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO tasks(subject,title,deadline) VALUES (?,?,?)",
                (subject, title, deadline))
        return int(cursor.lastrowid)

    def all(self) -> list[Task]:
        rows = self.connection.execute(
            "SELECT id,subject,title,deadline,completed FROM tasks")
        return [Task(a, b, c, d, bool(e)) for a, b, c, d, e in rows]

    def complete(self, task_id: int) -> bool:
        with self.connection:
            return self.connection.execute(
                "UPDATE tasks SET completed=1 WHERE id=?", (task_id,)
            ).rowcount > 0

    def edit(self, task_id: int, deadline: str) -> bool:
        with self.connection:
            return self.connection.execute(
                "UPDATE tasks SET deadline=? WHERE id=?", (deadline, task_id)
            ).rowcount > 0

    def delete(self, task_id: int) -> bool:
        with self.connection:
            return self.connection.execute(
                "DELETE FROM tasks WHERE id=?", (task_id,)
            ).rowcount > 0

    def replace_all(self, tasks: list[Task]) -> None:
        """Відновлення знімка в одній транзакції; помилка скасовує зміни."""
        with self.connection:
            self.connection.execute("DELETE FROM tasks")
            self.connection.executemany(
                "INSERT INTO tasks(id,subject,title,deadline,completed) "
                "VALUES (?,?,?,?,?)",
                [(t.id, t.subject, t.title, t.deadline, int(t.completed))
                 for t in tasks])

    def close(self) -> None:
        self.connection.close()
