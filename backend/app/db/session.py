from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
    # Connection pool settings to prevent thread exhaustion
    pool_size=5,          # Max 5 persistent connections
    max_overflow=10,      # Allow 10 extra connections when pool full
    pool_timeout=30,      # Wait max 30s for a connection
    pool_recycle=1800,    # Recycle connections every 30 min
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
