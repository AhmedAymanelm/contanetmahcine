import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.join(os.path.dirname(__file__)))
from app.db.session import SessionLocal

# Import ALL models so SQLAlchemy relationships resolve properly
from app.models.source import Source
from app.models.raw_article import RawArticle
from app.models.content_item import ContentItem
from app.models.carousel_template import CarouselTemplate

db = SessionLocal()

# Delete anything older than today's start (or just 24h ago to be safe, let's do 24h ago)
threshold = datetime.now(timezone.utc) - timedelta(hours=24)
print(f"Deleting articles older than {threshold}...")

# 1. Delete old ContentItems first (foreign key dependency)
deleted_content = db.query(ContentItem).filter(ContentItem.created_at < threshold).delete(synchronize_session=False)

# 2. Delete old RawArticles
deleted_raw = db.query(RawArticle).filter(RawArticle.created_at < threshold).delete(synchronize_session=False)

db.commit()

print(f"Deleted {deleted_content} old ContentItems.")
print(f"Deleted {deleted_raw} old RawArticles.")
