from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import concurrent.futures

from app.api.deps import get_db
from app.models.raw_article import RawArticle
from app.schemas.raw_article import RawArticleResponse
from datetime import datetime, timedelta, timezone
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
    # Show articles from the last 24 hours only (rolling window)
    display_cutoff = datetime.utcnow() - timedelta(hours=24)
    articles = db.query(RawArticle).filter(
        RawArticle.status == "PENDING",
        RawArticle.created_at >= display_cutoff
    ).order_by(RawArticle.created_at.desc()).limit(200).all()
    return articles

@router.get("/generating", response_model=List[RawArticleResponse])
def get_generating_articles(db: Session = Depends(get_db)):
    display_cutoff = datetime.utcnow() - timedelta(hours=24)
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
    carousel_platforms: List[str] = ["IG", "Li"]

@router.post("/{article_id}/generate")
def generate_article_content(article_id: int, request: ArticleGenerateRequest, db: Session = Depends(get_db)):
    article = db.query(RawArticle).filter(RawArticle.id == article_id).first()
    if not article:
        return {"error": "Article not found"}
        
    article.status = "APPROVED_FOR_GENERATION"
    db.commit()
    db.close()
    
    # Run in thread pool so it doesn't block FastAPI's event loop
    _thread_pool.submit(process_article_generation, article_id, request.formats, request.carousel_platforms)
    logger.info(f"Generation task submitted for article {article_id} with formats {request.formats}, carousel_platforms {request.carousel_platforms}")
    return {"detail": "Generation started in the background"}

@router.delete("/{article_id}")
def delete_raw_article(article_id: int, db: Session = Depends(get_db)):
    """Manually reject and delete a raw article."""
    article = db.query(RawArticle).filter(RawArticle.id == article_id).first()
    if not article:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"detail": "Article deleted"}
