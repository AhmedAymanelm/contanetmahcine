from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.source import Source
from app.models.raw_article import RawArticle
from app.services.ingestion.pipeline import process_source
from app.services.ingestion import health_monitor

def ingest_all_active_sources(db: Session):
    active_sources = db.query(Source).filter(Source.is_active == True).all()
    
    for source in active_sources:
        print(f"Ingesting from source: {source.name}")
        scraped_data = process_source(source.url)
            
        if not scraped_data:
            health_monitor.report_failure(db, source)
            continue
            
        health_monitor.report_success(db, source)
        
        for data in scraped_data:
            if not data.get("url"):
                continue
                
            existing = db.query(RawArticle).filter(RawArticle.url == data["url"]).first()
            if not existing:
                new_article = RawArticle(
                    source_id=source.id,
                    title=data["title"],
                    url=data["url"],
                    content=data["content"],
                    # published_at ideally needs date parsing from string
                    status="PENDING"
                )
                db.add(new_article)
        
        source.last_scraped_at = datetime.now(timezone.utc)
        db.commit()
    print("Ingestion complete.")
