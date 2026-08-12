from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import concurrent.futures

from app.api.deps import get_db
from app.models.raw_article import RawArticle
from app.schemas.raw_article import RawArticleResponse
from datetime import datetime, timedelta
from app.services.ingestion.runner import ingest_all_active_sources
from app.services.generation.runner import process_article_generation
import logging

logger = logging.getLogger(__name__)
_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

router = APIRouter()

def get_start_of_day_utc():
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc + timedelta(hours=3) # Africa/Cairo GMT+3
    start_of_day_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_day_utc = start_of_day_local - timedelta(hours=3)
    return start_of_day_utc.replace(tzinfo=None)

@router.get("/", response_model=List[RawArticleResponse])
def get_raw_articles(db: Session = Depends(get_db)):
    # Auto-cleanup: Delete pending articles older than 24 hours ONLY if they don't have ContentItems
    cleanup_cutoff = datetime.utcnow() - timedelta(hours=24)
    from app.models.content_item import ContentItem
    subquery = db.query(ContentItem.raw_article_id).subquery()
    db.query(RawArticle).filter(
        RawArticle.status == "PENDING", 
        RawArticle.created_at < cleanup_cutoff,
        ~RawArticle.id.in_(subquery)
    ).delete(synchronize_session=False)
    db.commit()
    
    # Filter for UI: Only show articles from TODAY (since midnight local time)
    display_cutoff = get_start_of_day_utc()
    articles = db.query(RawArticle).filter(
        RawArticle.status == "PENDING",
        RawArticle.created_at >= display_cutoff
    ).order_by(RawArticle.created_at.desc()).limit(100).all()
    return articles

@router.get("/generating", response_model=List[RawArticleResponse])
def get_generating_articles(db: Session = Depends(get_db)):
    display_cutoff = get_start_of_day_utc()
    articles = db.query(RawArticle).filter(
        RawArticle.status == "APPROVED_FOR_GENERATION",
        RawArticle.created_at >= display_cutoff
    ).order_by(RawArticle.created_at.desc()).all()
    return articles

@router.post("/ingest")
def trigger_ingestion(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Trigger ingestion in the background to avoid blocking the API response
    background_tasks.add_task(ingest_all_active_sources, db)
    return {"detail": "Ingestion started in the background"}

from pydantic import BaseModel

class ArticleGenerateRequest(BaseModel):
    formats: List[str] = ["POST", "CAROUSEL", "VIDEO_SCRIPT"]

@router.post("/{article_id}/generate")
def generate_article_content(article_id: int, request: ArticleGenerateRequest, db: Session = Depends(get_db)):
    article = db.query(RawArticle).filter(RawArticle.id == article_id).first()
    if not article:
        return {"error": "Article not found"}
        
    article.status = "APPROVED_FOR_GENERATION"
    db.commit()
    db.close()
    
    # Run in thread pool so it doesn't block FastAPI's event loop
    _thread_pool.submit(process_article_generation, article_id, request.formats)
    logger.info(f"Generation task submitted for article {article_id} with formats {request.formats}")
    return {"detail": "Generation started in the background"}
