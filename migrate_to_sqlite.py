"""
Migration script: Neon PostgreSQL → SQLite
Run this locally to create a populated SQLite DB, then upload to Railway.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

NEON_URL = "postgresql://neondb_owner:npg_PMQSiT8U7pqx@ep-wispy-boat-axmhjc1p-pooler.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require"
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "db_migrated.sqlite3")
SQLITE_URL  = f"sqlite:///{SQLITE_PATH}"

print(f"Source:      Neon PostgreSQL")
print(f"Destination: {SQLITE_PATH}\n")

from app.models.base import Base
import app.models.source, app.models.raw_article, app.models.content_item
import app.models.carousel_template, app.models.app_setting
import app.models.user, app.models.oauth_token, app.models.banned_word

sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=sqlite_engine)

with sqlite_engine.connect() as c:
    c.execute(text("PRAGMA journal_mode=WAL"))

neon_engine = create_engine(NEON_URL.replace("&channel_binding=require", ""))
inspector = inspect(neon_engine)
tables = inspector.get_table_names()

TABLE_ORDER = ["users","sources","raw_articles","carousel_templates",
               "content_items","app_settings","oauth_tokens","banned_words"]
for t in tables:
    if t not in TABLE_ORDER and t != "alembic_version":
        TABLE_ORDER.append(t)

total = 0
with neon_engine.connect() as neon_conn:
    with sqlite_engine.connect() as sq_conn:
        for table in TABLE_ORDER:
            if table not in tables:
                continue
            result = neon_conn.execute(text(f'SELECT * FROM "{table}"'))
            rows = result.fetchall()
            cols = list(result.keys())
            if not rows:
                print(f"  -- {table}: 0 rows")
                continue
            sq_conn.execute(text(f'DELETE FROM "{table}"'))
            col_str = ", ".join(f'"{c}"' for c in cols)
            ph = ", ".join(f":{c}" for c in cols)
            ins = text(f'INSERT OR REPLACE INTO "{table}" ({col_str}) VALUES ({ph})')
            ok = err = 0
            for row in rows:
                d = dict(zip(cols, row))
                import json
                for k, v in d.items():
                    # SQLite can't store Python dicts/lists — convert to JSON strings
                    if isinstance(v, (dict, list)):
                        d[k] = json.dumps(v, ensure_ascii=False)
                try:
                    sq_conn.execute(ins, d); ok += 1
                except Exception as e:
                    err += 1
                    if err <= 2: print(f"    ERR {table}: {e}")
            sq_conn.commit()
            total += ok
            print(f"  {'OK' if not err else 'WARN'} {table}: {ok} rows{f' ({err} errors)' if err else ''}")

print(f"\nDone! {total} total rows -> {SQLITE_PATH}")
