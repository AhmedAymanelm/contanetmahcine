from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from app.models.base import Base

class CarouselTemplate(Base):
    __tablename__ = "carousel_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    cover_bg_path = Column(String, nullable=True)
    body_bg_path = Column(String, nullable=True)
    cta_bg_path = Column(String, nullable=True)
    text_color = Column(String, default="#ffffff")
    accent_color = Column(String, default="#3b82f6")
    style_mode = Column(String, default="glass_mixed")
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
