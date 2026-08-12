#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values

DEFAULT_SOURCE_DB = os.path.join(os.path.dirname(__file__), "content_machine.db")
DEFAULT_TARGET_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_PMQSiT8U7pqx@ep-wispy-boat-axmhjc1p-pooler.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
)

TABLES_IN_ORDER = [
    "sources",
    "raw_articles",
    "content_items",
    "banned_words",
    "carousel_templates",
    "oauth_tokens",
]

CREATE_TABLE_SQL = {
    "sources": '''
        CREATE TABLE IF NOT EXISTS sources (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            scraping_type TEXT NOT NULL,
            interval_mins INTEGER DEFAULT 60,
            last_scraped_at TIMESTAMPTZ,
            is_active BOOLEAN DEFAULT TRUE,
            error_count INTEGER DEFAULT 0,
            health_status TEXT DEFAULT 'HEALTHY'
        );
    ''',
    "raw_articles": '''
        CREATE TABLE IF NOT EXISTS raw_articles (
            id SERIAL PRIMARY KEY,
            source_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            content TEXT,
            image_url TEXT,
            published_at TIMESTAMPTZ,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    ''',
    "content_items": '''
        CREATE TABLE IF NOT EXISTS content_items (
            id SERIAL PRIMARY KEY,
            raw_article_id INTEGER,
            content_type TEXT NOT NULL,
            status TEXT DEFAULT 'DRAFT',
            platforms JSONB DEFAULT '[]'::jsonb,
            generated_content JSONB NOT NULL,
            scheduled_at TIMESTAMPTZ,
            published_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    ''',
    "banned_words": '''
        CREATE TABLE IF NOT EXISTS banned_words (
            id SERIAL PRIMARY KEY,
            word TEXT UNIQUE NOT NULL,
            replacement TEXT
        );
    ''',
    "carousel_templates": '''
        CREATE TABLE IF NOT EXISTS carousel_templates (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            cover_bg_path TEXT,
            body_bg_path TEXT,
            cta_bg_path TEXT,
            text_color TEXT DEFAULT '#ffffff',
            accent_color TEXT DEFAULT '#3b82f6',
            style_mode TEXT DEFAULT 'glass_mixed',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    ''',
    "oauth_tokens": '''
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            id SERIAL PRIMARY KEY,
            platform TEXT UNIQUE,
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            account_id TEXT,
            open_id TEXT,
            scopes TEXT,
            expires_at TIMESTAMPTZ,
            refresh_expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    ''',
}

DATETIME_COLUMNS = {
    "created_at",
    "published_at",
    "scheduled_at",
    "last_scraped_at",
    "expires_at",
    "updated_at",
    "refresh_expires_at",
}

JSON_COLUMNS = {"platforms", "generated_content"}


def normalize_value(column_name, value):
    if column_name == "title" and value is None:
        return "Untitled"
        
    if value is None:
        return None

    if column_name in DATETIME_COLUMNS:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            for fmt in (
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
            ):
                try:
                    return datetime.strptime(value, fmt).isoformat()
                except ValueError:
                    continue
            return value
        return str(value)

    if column_name in JSON_COLUMNS:
        if isinstance(value, str):
            try:
                # Test parse but return string for postgres
                json.loads(value)
                return value
            except Exception:
                return '[]' if column_name == 'platforms' else '{}'
        elif isinstance(value, (dict, list)):
            return json.dumps(value)
        return '[]' if column_name == 'platforms' else '{}'

    if column_name == "is_active":
        return bool(value)
        
    if column_name == "title" and value is None:
        return "Untitled"

    if isinstance(value, str):
        value = value.strip()
        if column_name == "title" and value == "":
            return "Untitled"
        return value if value != "" else None

    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception:
            return value.decode("latin1", "replace")

    return value


def table_columns(conn, table_name):
    rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return [row[1] for row in rows]


def fetch_rows_from_sqlite(sqlite_path, table_name):
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        columns = table_columns(conn, table_name)
        if not columns:
            return []
        raw_rows = conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
        result = []
        for raw_row in raw_rows:
            row = {}
            for idx, column_name in enumerate(columns):
                row[column_name] = normalize_value(column_name, raw_row[idx])
            result.append(row)
        return result
    finally:
        conn.close()


def ensure_target_tables(conn):
    with conn.cursor() as cur:
        for table_name in TABLES_IN_ORDER:
            cur.execute(CREATE_TABLE_SQL[table_name])
            cur.execute(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE')


def main():
    source_db = os.environ.get("SOURCE_DB", DEFAULT_SOURCE_DB)
    target_url = os.environ.get("DATABASE_URL", DEFAULT_TARGET_URL)

    print(f"Source SQLite: {source_db}")
    print(f"Target PostgreSQL: {target_url}")

    if not os.path.exists(source_db):
        raise FileNotFoundError(f"SQLite source database not found: {source_db}")

    try:
        conn = psycopg2.connect(target_url)
    except Exception as exc:
        raise RuntimeError(f"Could not connect to target PostgreSQL: {exc}") from exc

    try:
        ensure_target_tables(conn)

        total = 0
        for table_name in TABLES_IN_ORDER:
            rows = fetch_rows_from_sqlite(source_db, table_name)
            if not rows:
                print(f"{table_name}: 0 rows (skipped)")
                continue

            columns = list(rows[0].keys())
            values = [tuple(row.get(c) for c in columns) for row in rows]
            insert_sql = (
                f'INSERT INTO "{table_name}" ({", ".join(f'"{c}"' for c in columns)}) '
                f'VALUES %s'
            )
            with conn:
                with conn.cursor() as cur:
                    execute_values(cur, insert_sql, values)
            print(f"{table_name}: migrated {len(values)} rows")
            total += len(values)

        print(f"Migration finished successfully. Total migrated rows: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
