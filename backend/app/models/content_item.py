from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models.base import Base

class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)
    raw_article_id = Column(Integer, ForeignKey("raw_articles.id"), nullable=True)
    content_type = Column(String, nullable=False)  # POST, CAROUSEL, VIDEO_SCRIPT
    status = Column(String, default="DRAFT")  # DRAFT, REVIEW, APPROVED, SCHEDULED, PUBLISHED
    platforms = Column(JSON, default=list)  # ["IG", "FB", "X", "Li", "TT"]
    generated_content = Column(JSON, nullable=False)  # The structured output from Claude
    
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    raw_article = relationship("RawArticle", backref="generated_content_items")
