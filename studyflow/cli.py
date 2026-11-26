"""Facade, Strategy та Command для командного інтерфейсу."""
import shlex
from dataclasses import dataclass
from typing import Callable, Protocol
from .core import Task, TaskService


class IO(Protocol):
    def read(self, prompt: str) -> str: ...
    def write(self, text: str) -> None: ...


class ConsoleIO:
    def read(self, prompt: str) -> str:
        return input(prompt)

    def write(self, text: str) -> None:
        print(text)


@dataclass(frozen=True)
class Args:
    name: str
    values: tuple[str, ...]


class ArgsParser:
    def parse(self, raw: str) -> Args | None:
        parts = shlex.split(raw)
        if not parts:
            return None
        return Args(parts[0].lower(), tuple(parts[1:]))


class Renderer(Protocol):
    def render(self, value: object) -> str: ...


class TextRenderer:
    def render(self, value: object) -> str:
        if isinstance(value, list):
            if not value:
                return "Завдань немає."
            header = "ID | Статус | Дедлайн | Предмет | Завдання"
            rows = [header, "-" * len(header)]
            for task in value:
                if not isinstance(task, Task):
                    raise TypeError("Очікується список завдань")
                status = "Виконано" if task.completed else "Активне"
                rows.append(f"{task.id} | {status} | {task.deadline} | "
                            f"{task.subject} | {task.title}")
            return "\n".join(rows)
        if isinstance(value, dict):
            return "\n".join(f"{k}: {v}" for k, v in value.items())
        return str(value)


@dataclass(frozen=True)
class Command:
    """Інкапсулює дію, аргументи та довідку для команди."""
    name: str
    usage: str
    action: Callable[["CLI", tuple[str, ...]], None]

    def execute(self, cli: "CLI", values: tuple[str, ...]) -> None:
        self.action(cli, values)


class CommandStrategy(Protocol):
    def commands(self) -> list[Command]: ...


def require(values: tuple[str, ...], count: int, usage: str) -> None:
    if len(values) != count:
        raise ValueError(f"Синтаксис: {usage}")


class QueryStrategy:
    def commands(self) -> list[Command]:
        return [
            Command("list", "list", self.list_tasks),
            Command("today", "today", self.today),
            Command("week", "week", self.week),
            Command("stats", "stats", self.stats),
        ]

    @staticmethod
    def list_tasks(cli: "CLI", values: tuple[str, ...]) -> None:
        require(values, 0, "list")
        cli.display(cli.service.list(cli.mode))

    @staticmethod
    def today(cli: "CLI", values: tuple[str, ...]) -> None:
        require(values, 0, "today")
        cli.display(cli.service.list(cli.mode, "today"))

    @staticmethod
    def week(cli: "CLI", values: tuple[str, ...]) -> None:
        require(values, 0, "week")
        cli.display(cli.service.list(cli.mode, "week"))

    @staticmethod
    def stats(cli: "CLI", values: tuple[str, ...]) -> None:
        require(values, 0, "stats")
        cli.display(cli.service.stats())


class ActionStrategy:
    def commands(self) -> list[Command]:
        return [
            Command("add", 'add "предмет" "назва" "YYYY-MM-DD HH:MM"', self.add),
            Command("done", "done ID", self.done),
            Command("edit", 'edit ID "YYYY-MM-DD HH:MM"', self.edit),
            Command("delete", "delete ID", self.delete),
        ]

    @staticmethod
    def add(cli: "CLI", values: tuple[str, ...]) -> None:
        if not values:
            values = (cli.io.read("Предмет: "), cli.io.read("Назва: "),
                      cli.io.read("Дедлайн (YYYY-MM-DD HH:MM): "))
        require(values, 3, 'add "предмет" "назва" "YYYY-MM-DD HH:MM"')
        task_id = cli.service.add(*values)
        cli.display(f"Завдання №{task_id} додано.")

    @staticmethod
    def done(cli: "CLI", values: tuple[str, ...]) -> None:
        require(values, 1, "done ID")
        cli.service.done(int(values[0]))
        cli.display("Завдання виконано.")

    @staticmethod
    def edit(cli: "CLI", values: tuple[str, ...]) -> None:
        require(values, 2, 'edit ID "YYYY-MM-DD HH:MM"')
        cli.service.edit(int(values[0]), values[1])
        cli.display("Дедлайн оновлено.")

    @staticmethod
    def delete(cli: "CLI", values: tuple[str, ...]) -> None:
        require(values, 1, "delete ID")
        cli.service.delete(int(values[0]))
        cli.display("Завдання видалено.")


class SystemStrategy:
    def commands(self) -> list[Command]:
        return [Command("help", "help", self.help),
                Command("mode", "mode all|active|completed", self.mode),
                Command("exit", "exit", self.exit)]

    @staticmethod
    def help(cli: "CLI", values: tuple[str, ...]) -> None:
        require(values, 0, "help")
        cli.display("\n".join(c.usage for c in cli.commands.values()))

    @staticmethod
    def mode(cli: "CLI", values: tuple[str, ...]) -> None:
        require(values, 1, "mode all|active|completed")
        if values[0] not in ("all", "active", "completed"):
            raise ValueError("Невідомий режим")
        cli.mode = values[0]
        cli.display(f"Режим: {cli.mode}")

    @staticmethod
    def exit(cli: "CLI", values: tuple[str, ...]) -> None:
        require(values, 0, "exit")
        cli.running = False


class CLI:
    """Фасад: реєстрація, розбір, виконання і представлення команд."""
    def __init__(self, service: TaskService, io: IO, renderer: Renderer,
                 mode: str = "all"):
        self.service = service
        self.io = io
        self.renderer = renderer
        self.mode = mode
        self.parser = ArgsParser()
        self.commands: dict[str, Command] = {}
        self.running = True

    def use_strategy(self, strategy: CommandStrategy) -> None:
        commands = strategy.commands()
        names = [command.name for command in commands]
        if len(names) != len(set(names)) or any(n in self.commands for n in names):
            raise ValueError("Повторна реєстрація команди")
        self.commands.update((c.name, c) for c in commands)

    def display(self, value: object) -> None:
        self.io.write(self.renderer.render(value))

    def exec_command(self, raw: str) -> None:
        try:
            args = self.parser.parse(raw)
            if args is None:
                return
            command = self.commands.get(args.name)
            if command is None:
                raise ValueError("Невідома команда. Введіть help.")
            command.execute(self, args.values)
        except ValueError as exc:
            self.display(f"Помилка: {exc}")

    def run(self) -> None:
        self.display("StudyFlow — Трасковський Богдан. Введіть help.")
        while self.running:
            try:
                self.exec_command(self.io.read(f"studyflow[{self.mode}]> "))
            except (EOFError, KeyboardInterrupt):
                self.running = False
        self.display("До побачення!")
