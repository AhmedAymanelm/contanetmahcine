from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

_db_url = settings.DATABASE_URL.replace("&channel_binding=require", "").replace("channel_binding=require&", "")

_is_sqlite = _db_url.startswith("sqlite")

if _is_sqlite:
    # SQLite: no pooling, check_same_thread=False for multi-threaded FastAPI
    engine = create_engine(
        _db_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    # Enable WAL mode for better concurrent reads
    @event.listens_for(engine, "connect")
    def set_wal_mode(dbapi_conn, connection_record):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA synchronous=NORMAL")
        dbapi_conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
else:
    # PostgreSQL (Neon): connection pool + keepalive
    connect_args = {
        "keepalives": 1,
        "keepalives_idle": 60,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "connect_timeout": 10,
    }
    engine = create_engine(
        _db_url,
        pool_pre_ping=True,
        connect_args=connect_args,
        pool_size=3,
        max_overflow=7,
        pool_timeout=30,
        pool_recycle=240,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
