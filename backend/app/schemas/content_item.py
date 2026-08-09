from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.schemas.raw_article import RawArticleResponse

class ContentItemBase(BaseModel):
    content_type: str
    status: str
    platforms: List[str]
    generated_content: Dict[str, Any]

class ContentItemUpdate(BaseModel):
    generated_content: Dict[str, Any]

class ContentItemResponse(ContentItemBase):
    id: int
    raw_article_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    
    raw_article: Optional[RawArticleResponse] = None

    class Config:
        from_attributes = True
