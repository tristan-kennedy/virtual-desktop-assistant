from pathlib import Path
import sys


def main() -> None:
    project_src = Path(__file__).resolve().parent / "src"

    if str(project_src) not in sys.path:
        sys.path.insert(0, str(project_src))

    from dipsy_dolphin.__main__ import main as package_main

    package_main()


if __name__ == "__main__":
    main()
