"""Точка входу StudyFlow."""
import argparse

from studyflow.core import TaskService
from studyflow.data import SQLiteRepository
from studyflow.persistence import JsonSnapshotStore, default_database_path
from studyflow.cli import (
    CLI, ConsoleIO, TextRenderer, QueryStrategy, ActionStrategy,
    SystemStrategy, PersistenceStrategy,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="StudyFlow")
    parser.add_argument("--mode", choices=["all", "active", "completed"], default="all")
    parser.add_argument("--db", help="Шлях до бази SQLite")
    parser.add_argument("--gui", action="store_true", help="Графічний інтерфейс")
    args = parser.parse_args()
    repository = SQLiteRepository(args.db or str(default_database_path()))
    try:
        service = TaskService(repository)
        snapshots = JsonSnapshotStore(repository)
        if args.gui:
            from studyflow.gui import run_gui
            from studyflow.gui_controller import PlannerController
            run_gui(PlannerController(service, snapshots), args.mode)
            return
        cli = CLI(service, ConsoleIO(), TextRenderer(), args.mode)
        for strategy in (QueryStrategy(), ActionStrategy(), SystemStrategy(),
                         PersistenceStrategy(snapshots)):
            cli.use_strategy(strategy)
        cli.run()
    finally:
        repository.close()


if __name__ == "__main__":
    main()
