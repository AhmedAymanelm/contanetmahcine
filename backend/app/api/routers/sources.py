from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.api.deps import get_db
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceResponse, SourceUpdate
from pydantic import BaseModel

class TestFetchRequest(BaseModel):
    url: str

router = APIRouter()

@router.get("/", response_model=List[SourceResponse])
def get_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).all()
    return sources

@router.post("/", response_model=SourceResponse)
def create_source(source_in: SourceCreate, db: Session = Depends(get_db)):
    new_source = Source(**source_in.model_dump())
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return new_source

@router.put("/{source_id}/toggle", response_model=SourceResponse)
def toggle_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.is_active = not source.is_active
    db.commit()
    db.refresh(source)
    return source

@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
        
    from app.models.raw_article import RawArticle
    from app.models.content_item import ContentItem
    
    # 1. Find all raw articles for this source
    article_ids = [a.id for a in db.query(RawArticle.id).filter(RawArticle.source_id == source_id).all()]
    
    # 2. Delete all content items referencing those articles
    if article_ids:
        db.query(ContentItem).filter(ContentItem.raw_article_id.in_(article_ids)).delete(synchronize_session=False)
        
    # 3. Delete all raw articles for this source
    db.query(RawArticle).filter(RawArticle.source_id == source_id).delete(synchronize_session=False)
    
    # 4. Delete the source itself
    db.delete(source)
    db.commit()
    return {"detail": "Source deleted"}

@router.post("/test-fetch")
def test_fetch_source(request: TestFetchRequest):
    from app.services.ingestion.pipeline import process_source
    articles = process_source(request.url)
    return {"articles": articles[:3], "success": len(articles) > 0}

@router.post("/run-ingestion")
def run_ingestion(db: Session = Depends(get_db)):
    from app.services.ingestion.pipeline import process_source
    from app.models.raw_article import RawArticle
    
    # 1. Get all active sources
    active_sources = db.query(Source).filter(Source.is_active == True).all()
    
    total_scraped = 0
    # 2. Process each
    for source in active_sources:
        try:
            articles = process_source(source.url)
            # Save to DB
            for art in articles:
                # Check if exists by URL
                exists = db.query(RawArticle).filter(RawArticle.url == art["url"]).first()
                if not exists:
                    new_art = RawArticle(
                        source_id=source.id,
                        title=art["title"],
                        url=art["url"],
                        content=art["content"],
                        image_url=art.get("image_url"),
                        published_at=None # Can parse later if needed
                    )
                    db.add(new_art)
                    total_scraped += 1
            
            source.last_scraped_at = datetime.utcnow()
            source.error_count = 0
            source.health_status = 'ok'
            db.commit()
            
        except Exception as e:
            print(f"Error scraping {source.url}: {e}")
            source.error_count += 1
            if source.error_count >= 3:
                source.health_status = 'needs_review'
            db.commit()
            
    return {"detail": f"Ingestion completed. Scraped {total_scraped} new articles."}
