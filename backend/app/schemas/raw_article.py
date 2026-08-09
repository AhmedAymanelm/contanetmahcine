from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.source import SourceResponse

class RawArticleBase(BaseModel):
    title: str
    url: str
    content: Optional[str] = None
    image_url: Optional[str] = None
    published_at: Optional[datetime] = None
    status: str

class RawArticleResponse(RawArticleBase):
    id: int
    source_id: int
    published_at: Optional[datetime] = None
    created_at: datetime
    
    # We might not always load source, but if we do, here it is
    source: Optional[SourceResponse] = None

    class Config:
        from_attributes = True
