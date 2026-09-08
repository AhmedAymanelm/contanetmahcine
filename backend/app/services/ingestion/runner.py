from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.source import Source
from app.models.raw_article import RawArticle
from app.services.ingestion.pipeline import process_source
from app.services.ingestion import health_monitor
from app.services.ingestion.relevance_filter import is_tech_relevant
import logging

logger = logging.getLogger(__name__)

def ingest_all_active_sources(db: Session):
    active_sources = db.query(Source).filter(Source.is_active == True).all()
    
    for source in active_sources:
        logger.info(f"Ingesting from source: {source.name}")
        scraped_data = process_source(source.url)
            
        if not scraped_data:
            health_monitor.report_failure(db, source)
            continue
            
        health_monitor.report_success(db, source)
        
        saved = 0
        skipped = 0
        for data in scraped_data:
            if not data.get("url"):
                continue
            
            title   = data.get("title", "")
            content = data.get("content", "")

            # ── Relevance filter: only AI & tech articles ──
            if not is_tech_relevant(title, content):
                logger.info(f"Skipped (not tech/AI): {title[:60]}")
                skipped += 1
                continue

            existing = db.query(RawArticle).filter(RawArticle.url == data["url"]).first()
            if not existing:
                new_article = RawArticle(
                    source_id=source.id,
                    title=title,
                    url=data["url"],
                    content=content,
                    image_url=data.get("image_url", ""),
                    status="PENDING"
                )
                db.add(new_article)
                saved += 1
        
        source.last_scraped_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Source '{source.name}': saved={saved}, skipped(non-tech)={skipped}")

    logger.info("Ingestion complete.")
