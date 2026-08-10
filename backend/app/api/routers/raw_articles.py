from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.models.raw_article import RawArticle
from app.schemas.raw_article import RawArticleResponse
from datetime import datetime, timedelta
from app.services.ingestion.runner import ingest_all_active_sources
from app.services.generation.runner import process_article_generation

router = APIRouter()

@router.get("/", response_model=List[RawArticleResponse])
def get_raw_articles(db: Session = Depends(get_db)):
    # Auto-cleanup: Delete pending articles older than 24 hours ONLY if they don't have ContentItems
    cutoff = datetime.utcnow() - timedelta(hours=24)
    from app.models.content_item import ContentItem
    subquery = db.query(ContentItem.raw_article_id).subquery()
    db.query(RawArticle).filter(
        RawArticle.status == "PENDING", 
        RawArticle.created_at < cutoff,
        ~RawArticle.id.in_(subquery)
    ).delete(synchronize_session=False)
    db.commit()
    
    articles = db.query(RawArticle).filter(
        RawArticle.status == "PENDING",
        RawArticle.created_at >= cutoff
    ).order_by(RawArticle.created_at.desc()).limit(100).all()
    return articles

@router.get("/generating", response_model=List[RawArticleResponse])
def get_generating_articles(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(hours=24)
    articles = db.query(RawArticle).filter(
        RawArticle.status == "APPROVED_FOR_GENERATION",
        RawArticle.created_at >= cutoff
    ).order_by(RawArticle.created_at.desc()).all()
    return articles

@router.post("/ingest")
def trigger_ingestion(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Trigger ingestion in the background to avoid blocking the API response
    background_tasks.add_task(ingest_all_active_sources, db)
    return {"detail": "Ingestion started in the background"}

@router.post("/{article_id}/generate")
def generate_article_content(article_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    article = db.query(RawArticle).filter(RawArticle.id == article_id).first()
    if not article:
        return {"error": "Article not found"}
        
    article.status = "APPROVED_FOR_GENERATION"
    db.commit()
    
    background_tasks.add_task(process_article_generation, article_id)
    return {"detail": "Generation started in the background"}
