import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__)))
from app.db.session import SessionLocal
from app.models.source import Source
from app.models.raw_article import RawArticle
from app.models.content_item import ContentItem
from app.models.carousel_template import CarouselTemplate

db = SessionLocal()

# Delete ALL content items and raw articles to start completely fresh!
deleted_content = db.query(ContentItem).delete(synchronize_session=False)
deleted_raw = db.query(RawArticle).delete(synchronize_session=False)

db.commit()

print(f"Completely wiped {deleted_content} ContentItems and {deleted_raw} RawArticles from the database!")
