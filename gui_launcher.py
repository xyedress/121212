"""Точка входу графічної версії для Windows."""
import sys
from main import main


if __name__ == "__main__":
    main(["--gui", *sys.argv[1:]])
