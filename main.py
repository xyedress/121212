"""Точка входу StudyFlow."""
import argparse
from studyflow.core import TaskService
from studyflow.data import SQLiteRepository
from studyflow.cli import CLI, ConsoleIO, TextRenderer, QueryStrategy, ActionStrategy, SystemStrategy


def main() -> None:
    parser = argparse.ArgumentParser(description="StudyFlow")
    parser.add_argument("--mode", choices=["all", "active", "completed"], default="all")
    parser.add_argument("--db", default="studyflow.db")
    args = parser.parse_args()
    repository = SQLiteRepository(args.db)
    try:
        cli = CLI(TaskService(repository), ConsoleIO(), TextRenderer(), args.mode)
        for strategy in (QueryStrategy(), ActionStrategy(), SystemStrategy()):
            cli.use_strategy(strategy)
        cli.run()
    finally:
        repository.close()


if __name__ == "__main__":
    main()
