from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import psycopg
from psycopg import sql

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bot.services.db import Database


TABLE_ORDER = [
    "users",
    "config",
    "voice_channels",
    "auth_period_status",
    "warning_history",
]


def split_statements(script: str) -> list[str]:
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def sqlite_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in rows]


def ensure_target_is_empty(connection: psycopg.Connection, allow_non_empty: bool) -> None:
    if allow_non_empty:
        return

    with connection.cursor() as cursor:
        for table_name in TABLE_ORDER:
            cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}") .format(sql.Identifier(table_name)))
            row_count = cursor.fetchone()[0]
            if row_count:
                raise RuntimeError(
                    f"Target table '{table_name}' already has {row_count} rows. "
                    "Use --allow-non-empty only if you intend to merge into an existing database."
                )


def create_postgres_schema(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        for statement in split_statements(Database.POSTGRES_SCHEMA):
            cursor.execute(statement)
        for statement in split_statements(Database.INDEX_STATEMENTS):
            cursor.execute(statement)
    connection.commit()


def copy_table(sqlite_connection: sqlite3.Connection, postgres_connection: psycopg.Connection, table_name: str) -> int:
    columns = sqlite_columns(sqlite_connection, table_name)
    quoted_columns = sql.SQL(", ").join(sql.Identifier(column_name) for column_name in columns)
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)

    sqlite_rows = sqlite_connection.execute(f"SELECT * FROM {table_name} ORDER BY id").fetchall()
    if not sqlite_rows:
        return 0

    with postgres_connection.cursor() as cursor:
        insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table_name),
            quoted_columns,
            placeholders,
        )
        cursor.executemany(insert_query, sqlite_rows)
    postgres_connection.commit()
    return len(sqlite_rows)


def sync_sequence(connection: psycopg.Connection, table_name: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL(
                "SELECT setval(pg_get_serial_sequence(%s, 'id'), COALESCE(MAX(id), 1), COUNT(*) > 0) FROM {}"
            ).format(sql.Identifier(table_name)),
            (table_name,),
        )
    connection.commit()


def validate_table(sqlite_connection: sqlite3.Connection, postgres_connection: psycopg.Connection, table_name: str) -> None:
    sqlite_rows = sqlite_connection.execute(f"SELECT * FROM {table_name} ORDER BY id").fetchall()

    with postgres_connection.cursor() as cursor:
        cursor.execute(sql.SQL("SELECT * FROM {} ORDER BY id").format(sql.Identifier(table_name)))
        postgres_rows = cursor.fetchall()

    normalized_postgres_rows = [tuple(row) for row in postgres_rows]
    if sqlite_rows != normalized_postgres_rows:
        raise RuntimeError(f"Validation failed for table '{table_name}'. SQLite and PostgreSQL rows differ.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate a Sodabot SQLite database into PostgreSQL.")
    parser.add_argument("--sqlite-path", required=True, help="Path to the source SQLite database file")
    parser.add_argument(
        "--postgres-url",
        default=None,
        help="PostgreSQL connection string. Defaults to DATABASE_URL environment variable when omitted.",
    )
    parser.add_argument(
        "--allow-non-empty",
        action="store_true",
        help="Allow migrating into a PostgreSQL database that already contains rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

    postgres_url = args.postgres_url
    if not postgres_url:
        import os

        postgres_url = os.getenv("DATABASE_URL")
    if not postgres_url:
        raise RuntimeError("PostgreSQL connection string is required via --postgres-url or DATABASE_URL.")

    sqlite_connection = sqlite3.connect(sqlite_path)
    try:
        postgres_connection = psycopg.connect(postgres_url)
        try:
            create_postgres_schema(postgres_connection)
            ensure_target_is_empty(postgres_connection, args.allow_non_empty)

            for table_name in TABLE_ORDER:
                copied_count = copy_table(sqlite_connection, postgres_connection, table_name)
                sync_sequence(postgres_connection, table_name)
                validate_table(sqlite_connection, postgres_connection, table_name)
                print(f"{table_name}: copied {copied_count} rows")

            print("SQLite -> PostgreSQL migration completed successfully.")
        finally:
            postgres_connection.close()
    finally:
        sqlite_connection.close()


if __name__ == "__main__":
    main()