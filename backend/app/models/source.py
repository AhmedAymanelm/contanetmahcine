from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.models.base import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    url = Column(String, nullable=False)
    scraping_type = Column(String, nullable=False)  # RSS or Scraping
    interval_mins = Column(Integer, default=60)
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Health Monitoring Fields
    error_count = Column(Integer, default=0)
    health_status = Column(String, default="HEALTHY")  # HEALTHY, NEEDS_REVIEW, ERROR
