from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a consistent backup copy of a SQLite database file."
    )
    parser.add_argument("--source", required=True, help="Path to the source SQLite database file")
    parser.add_argument("--output", required=True, help="Path to write the backup SQLite database file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    source_path = Path(args.source)
    output_path = Path(args.output)

    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite source file not found: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    source_connection = sqlite3.connect(source_path)
    try:
        backup_connection = sqlite3.connect(output_path)
        try:
            source_connection.backup(backup_connection)
        finally:
            backup_connection.close()
    finally:
        source_connection.close()

    print(f"SQLite backup created: {output_path}")


if __name__ == "__main__":
    main()