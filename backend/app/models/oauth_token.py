from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from app.models.base import Base

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, unique=True, index=True)  # e.g., 'threads', 'tiktok'
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)          # TikTok & future platforms
    account_id = Column(String, nullable=True)           # Threads user ID / TikTok open_id
    open_id = Column(String, nullable=True)              # TikTok open_id (alias for account_id)
    scopes = Column(String, nullable=True)               # Space-separated granted scopes
    expires_at = Column(DateTime, nullable=True)
    refresh_expires_at = Column(DateTime, nullable=True) # TikTok refresh token expiry
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
