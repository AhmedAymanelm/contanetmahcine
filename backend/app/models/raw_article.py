from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models.base import Base

class RawArticle(Base):
    __tablename__ = "raw_articles"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    content = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="PENDING")  # PENDING, APPROVED_FOR_GENERATION, REJECTED, GENERATED
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    source = relationship("Source", backref="raw_articles")
