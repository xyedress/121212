"""SQLite-реалізація репозиторію."""
import sqlite3
from .core import Task


class SQLiteRepository:
    def __init__(self, path: str):
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               subject TEXT NOT NULL, title TEXT NOT NULL,
               deadline TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0
               )"""
        )
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

    def close(self) -> None:
        self.connection.close()
