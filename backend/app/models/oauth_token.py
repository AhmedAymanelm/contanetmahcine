from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.models.base import Base

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, unique=True, index=True)  # e.g., 'threads'
    access_token = Column(String, nullable=False)
    account_id = Column(String, nullable=True) # E.g., Threads user ID
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
