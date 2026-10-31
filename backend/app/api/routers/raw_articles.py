from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
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
async def get_raw_articles(db: Session = Depends(get_db)):
    # Show articles from the last 24 hours only (rolling window)
    display_cutoff = datetime.utcnow() - timedelta(hours=24)
    articles = db.query(RawArticle).filter(
        RawArticle.status.in_(["PENDING", "QUOTA_EXCEEDED"]),
        RawArticle.created_at >= display_cutoff
    ).order_by(RawArticle.created_at.desc()).limit(200).all()
    return articles

@router.get("/generating", response_model=List[RawArticleResponse])
async def get_generating_articles(db: Session = Depends(get_db)):
    from app.models.content_item import ContentItem
    articles = db.query(RawArticle).filter(
        RawArticle.status == "APPROVED_FOR_GENERATION"
    ).order_by(RawArticle.created_at.desc()).all()

    active_generating = []
    has_updates = False

    for art in articles:
        # If content items already exist for this article, mark as GENERATED so it leaves generating state
        items_count = db.query(ContentItem).filter(ContentItem.raw_article_id == art.id).count()
        if items_count > 0:
            art.status = "GENERATED"
            has_updates = True
            continue

        # If it has been stuck for more than 10 minutes with 0 items, auto-reset to PENDING
        created_time = art.created_at.replace(tzinfo=None) if art.created_at else datetime.utcnow()
        if (datetime.utcnow() - created_time).total_seconds() > 600:
            art.status = "PENDING"
            has_updates = True
            continue

        active_generating.append(art)

    if has_updates:
        try:
            db.commit()
        except Exception:
            db.rollback()

    return active_generating

@router.post("/ingest")
async def trigger_ingestion(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Trigger ingestion in the background to avoid blocking the API response
    _thread_pool.submit(ingest_all_active_sources, None)
    return {"detail": "Ingestion started in the background"}

from pydantic import BaseModel
from app.models.source import Source


class ArticleGenerateRequest(BaseModel):
    formats: List[str] = ["POST", "CAROUSEL", "VIDEO_SCRIPT"]
    carousel_platforms: List[str] = ["IG", "Li"]
    slides: Optional[List[Dict[str, Any]]] = None
    template_id: Optional[int] = None


class ManualArticleRequest(BaseModel):
    title: Optional[str] = ""
    content: Optional[str] = ""
    source_name: str = "يدوي"
    url: str = ""
    image_url: str = ""
    category: str = ""
    slides: Optional[List[Dict[str, Any]]] = None


@router.post("/manual")
async def create_manual_article(request: ManualArticleRequest, db: Session = Depends(get_db)):
    """Create a raw article manually without scraping."""
    import uuid as _uuid

    title = (request.title or "").strip()
    content = (request.content or "").strip()

    # If slides are provided, construct content/title from slides if missing
    if request.slides and isinstance(request.slides, list) and len(request.slides) > 0:
        slide_texts = []
        for i, s in enumerate(request.slides):
            h = (s.get("heading") or "").strip()
            b = (s.get("body") or "").strip()
            parts = [f"شريحة {i+1}:"]
            if h: parts.append(h)
            if b: parts.append(b)
            slide_texts.append(" - ".join(parts))
        if not content:
            content = "\n\n".join(slide_texts)
        if not title:
            first_h = (request.slides[0].get("heading") or "").strip()
            title = first_h if first_h else (content.split("\n")[0][:80] if content else "كاروسيل يدوي")

    # If only title or only content is provided, fill in the other
    if not title and content:
        title = content.split("\n")[0][:80].strip()
    if not content and title:
        content = title

    if not title and not content:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="يجب إدخال عنوان أو نص أو شرائح للخبر")

    # Find or create the manual source
    source = db.query(Source).filter(Source.name == "يدوي").first()
    if not source:
        source = Source(
            name="يدوي",
            url="manual://",
            scraping_type="Manual",
            is_active=False,
        )
        db.add(source)
        db.flush()  # get source.id without committing

    # Build a unique URL if none provided
    article_url = request.url.strip() if request.url.strip() else f"manual://{_uuid.uuid4()}"

    article = RawArticle(
        source_id=source.id,
        title=title,
        content=content,
        url=article_url,
        image_url=request.image_url or None,
        status="PENDING",
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    logger.info(f"Manual article created: id={article.id}, title={article.title}")
    return article

@router.post("/{article_id}/generate")
async def generate_article_content(article_id: int, request: ArticleGenerateRequest, db: Session = Depends(get_db)):
    article = db.query(RawArticle).filter(RawArticle.id == article_id).first()
    if not article:
        return {"error": "Article not found"}
        
    article.status = "APPROVED_FOR_GENERATION"
    db.commit()
    db.close()
    
    # Run in thread pool so it doesn't block FastAPI's event loop
    _thread_pool.submit(process_article_generation, article_id, request.formats, request.carousel_platforms, request.slides, request.template_id)
    logger.info(f"Generation task submitted for article {article_id} with formats {request.formats}, carousel_platforms {request.carousel_platforms}")
    return {"detail": "Generation started in the background"}

@router.delete("/{article_id}")
async def delete_raw_article(article_id: int, db: Session = Depends(get_db)):
    """Manually reject and delete a raw article."""
    article = db.query(RawArticle).filter(RawArticle.id == article_id).first()
    if not article:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"detail": "Article deleted"}

@router.post("/reset-stuck")
async def reset_stuck_articles(db: Session = Depends(get_db)):
    """Reset articles stuck in APPROVED_FOR_GENERATION back to PENDING.
    Useful after server restart kills running generation tasks."""
    stuck = db.query(RawArticle).filter(
        RawArticle.status == "APPROVED_FOR_GENERATION"
    ).all()
    count = len(stuck)
    for art in stuck:
        art.status = "PENDING"
    db.commit()
    logger.info(f"Reset {count} stuck articles back to PENDING")
    return {"detail": f"Reset {count} stuck articles to PENDING"}

@router.post("/{article_id}/retry")
async def retry_article_generation(article_id: int, request: ArticleGenerateRequest, db: Session = Depends(get_db)):
    """Force retry generation for a stuck article."""
    article = db.query(RawArticle).filter(RawArticle.id == article_id).first()
    if not article:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Article not found")
    article.status = "APPROVED_FOR_GENERATION"
    db.commit()
    db.close()
    _thread_pool.submit(process_article_generation, article_id, request.formats, request.carousel_platforms)
    logger.info(f"Retry generation submitted for article {article_id}")
    return {"detail": "Retry started"}

@router.get("/quota-status")
async def get_quota_status(db: Session = Depends(get_db)):
    """Returns the count of articles blocked by quota exceeded error."""
    blocked = db.query(RawArticle).filter(
        RawArticle.status == "QUOTA_EXCEEDED"
    ).count()
    return {"quota_exceeded": blocked > 0, "blocked_count": blocked}

@router.post("/retry-quota-exceeded")
async def retry_quota_exceeded(db: Session = Depends(get_db)):
    """Reset all QUOTA_EXCEEDED articles back to PENDING so they can be retried."""
    articles = db.query(RawArticle).filter(
        RawArticle.status == "QUOTA_EXCEEDED"
    ).all()
    count = len(articles)
    for art in articles:
        art.status = "PENDING"
    db.commit()
    logger.info(f"Reset {count} quota-exceeded articles back to PENDING")
    return {"detail": f"Reset {count} articles to PENDING"}
