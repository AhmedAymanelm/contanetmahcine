from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Remove channel_binding=require as it adds extra TLS overhead
# The pooler endpoint handles auth without needing channel binding
_db_url = settings.DATABASE_URL.replace("&channel_binding=require", "").replace("channel_binding=require&", "")

connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {
    # TCP keepalive: detect dead Neon connections quickly
    "keepalives": 1,
    "keepalives_idle": 60,       # Start keepalive after 60s idle
    "keepalives_interval": 10,   # Retry every 10s
    "keepalives_count": 5,       # Give up after 5 retries
    "connect_timeout": 10,       # Fail fast if Neon is down
}

engine = create_engine(
    _db_url,
    pool_pre_ping=True,          # Detect stale connections on checkout
    connect_args=connect_args,
    pool_size=3,                 # 3 persistent connections (reduced from 5)
    max_overflow=7,              # Allow 7 extra connections under load
    pool_timeout=30,             # Wait max 30s for a free connection
    pool_recycle=240,            # Recycle every 4 min — beats Neon's 5min
                                 # auto-suspend timer so pool stays warm
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
