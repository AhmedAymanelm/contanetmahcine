import logging
from sqlalchemy.orm import Session
from app.models.raw_article import RawArticle
from app.models.content_item import ContentItem
from app.ai.generation_pipeline import generate_selected_content

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

def process_article_generation(raw_article_id: int, formats: list = None):
    """
    Takes a RawArticle ID, sends it to Claude for generation,
    saves the results as ContentItems, and updates status.
    """
    if formats is None:
        formats = ["POST", "CAROUSEL", "VIDEO_SCRIPT"]
        
    db = SessionLocal()
    try:
        article = db.query(RawArticle).filter(RawArticle.id == raw_article_id).first()
        if not article:
            logger.error(f"Article {raw_article_id} not found for generation.")
            return

        # Call AI pipeline
        logger.info(f"Generating AI content for article: {article.title}")
        
        # We pass the full content if available, otherwise just the title
        text_to_process = article.content if article.content else article.title
        generated = generate_selected_content(article.title, text_to_process, formats)
        
        if not generated:
            logger.error("AI Generation failed or returned empty.")
            return

        # Create Content Items
        items_to_add = []
        
        # 1. Post
        if "posts" in generated and generated["posts"]:
            items_to_add.append(
                ContentItem(
                    raw_article_id=article.id,
                    content_type="POST",
                    status="pending_review",
                    platforms=["FB", "Li", "X"],
                    generated_content=generated["posts"]
                )
            )
            
        # 2. Carousel
        if "carousel" in generated and generated["carousel"]:
            items_to_add.append(
                ContentItem(
                    raw_article_id=article.id,
                    content_type="CAROUSEL",
                    status="pending_review",
                    platforms=["IG", "Li"],
                    generated_content=generated["carousel"]
                )
            )
            
        # 3. Video Script
        if "video_script" in generated and generated["video_script"]:
            items_to_add.append(
                ContentItem(
                    raw_article_id=article.id,
                    content_type="VIDEO_SCRIPT",
                    status="pending_review",
                    platforms=["TT", "IG"],
                    generated_content=generated["video_script"]
                )
            )
            
        if items_to_add:
            for item in items_to_add:
                db.add(item)
                
            # Update article status only if generation succeeded
            article.status = "GENERATED"
            db.commit()
            logger.info(f"Successfully generated content items for article {article.id}")
        else:
            logger.error(f"Claude returned empty content for article {article.id}. Status not updated.")
            # Leave it as PENDING or change to a failed state so it can be retried
            article.status = "PENDING"
            db.commit()
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        db.rollback()
        try:
            # Attempt to reset status on failure
            article = db.query(RawArticle).filter(RawArticle.id == raw_article_id).first()
            if article:
                article.status = "PENDING"
                db.commit()
        except:
            pass
    finally:
        db.close()

def process_trend_generation(trend_title: str, trend_snippet: str, formats: list = None):
    """
    Takes a Trend title and snippet, sends it to Claude for generation,
    and saves the results as ContentItems.
    """
    if formats is None:
        formats = ["POST", "CAROUSEL", "VIDEO_SCRIPT"]
        
    db = SessionLocal()
    try:
        logger.info(f"Generating AI content for Trend: {trend_title}")
        
        text_to_process = f"Trend: {trend_title}\n\nContext/News: {trend_snippet}"
        generated = generate_selected_content(trend_title, text_to_process, formats)
        
        if not generated:
            logger.error("AI Generation failed for trend.")
            return

        # Create Content Items
        items_to_add = []
        
        # Inject trend_title into all generated components to show up in the UI
        for key in generated:
            if isinstance(generated[key], dict):
                generated[key]["trend_title"] = trend_title
        
        # 1. Post
        if "posts" in generated and generated["posts"]:
            items_to_add.append(
                ContentItem(
                    raw_article_id=None,
                    content_type="POST",
                    status="pending_review",
                    platforms=["FB", "Li", "X"],
                    generated_content=generated["posts"]
                )
            )
            
        # 2. Carousel
        if "carousel" in generated and generated["carousel"]:
            items_to_add.append(
                ContentItem(
                    raw_article_id=None,
                    content_type="CAROUSEL",
                    status="pending_review",
                    platforms=["IG", "Li"],
                    generated_content=generated["carousel"]
                )
            )
            
        # 3. Video Script
        if "video_script" in generated and generated["video_script"]:
            items_to_add.append(
                ContentItem(
                    raw_article_id=None,
                    content_type="VIDEO_SCRIPT",
                    status="pending_review",
                    platforms=["TT", "IG"],
                    generated_content=generated["video_script"]
                )
            )
            
        if items_to_add:
            for item in items_to_add:
                db.add(item)
                
            db.commit()
            logger.info(f"Successfully generated content items for Trend: {trend_title}")
        else:
            logger.error(f"Claude returned empty content for Trend: {trend_title}")
    except Exception as e:
        logger.error(f"Trend Generation failed: {e}")
        db.rollback()
    finally:
        db.close()
