from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.models.raw_article import RawArticle
from app.schemas.raw_article import RawArticleResponse
from app.services.ingestion.runner import ingest_all_active_sources
from app.services.generation.runner import process_article_generation

router = APIRouter()

@router.get("/", response_model=List[RawArticleResponse])
def get_raw_articles(db: Session = Depends(get_db)):
    articles = db.query(RawArticle).filter(RawArticle.status == "PENDING").order_by(RawArticle.created_at.desc()).limit(100).all()
    return articles

@router.get("/generating", response_model=List[RawArticleResponse])
def get_generating_articles(db: Session = Depends(get_db)):
    articles = db.query(RawArticle).filter(RawArticle.status == "APPROVED_FOR_GENERATION").order_by(RawArticle.created_at.desc()).all()
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
