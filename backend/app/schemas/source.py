from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SourceBase(BaseModel):
    name: str
    url: str
    scraping_type: str
    interval_mins: int = 60
    is_active: bool = True

class SourceCreate(SourceBase):
    pass

class SourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    scraping_type: Optional[str] = None
    interval_mins: Optional[int] = None
    is_active: Optional[bool] = None

class SourceResponse(SourceBase):
    id: int
    last_scraped_at: Optional[datetime] = None

    class Config:
        from_attributes = True
