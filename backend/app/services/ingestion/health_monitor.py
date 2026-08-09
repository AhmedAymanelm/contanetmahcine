from sqlalchemy.orm import Session
from app.models.source import Source

MAX_FAILURES = 3

def report_success(db: Session, source: Source):
    source.error_count = 0
    source.health_status = "HEALTHY"
    db.commit()

def report_failure(db: Session, source: Source):
    source.error_count += 1
    if source.error_count >= MAX_FAILURES:
        source.health_status = "NEEDS_REVIEW"
    db.commit()
