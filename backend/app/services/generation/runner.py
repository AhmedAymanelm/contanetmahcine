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

        # Call AI pipeline — pass carousel platforms so language is chosen correctly
        # (Arabic for IG/FB/etc, English only when LinkedIn is the sole platform)
        carousel_platforms = ["IG", "Li"]  # default carousel platforms
        text_to_process = article.content if article.content else article.title
        generated = generate_selected_content(
            article.title, text_to_process, formats,
            platforms=carousel_platforms
        )
        
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
        
        draft_items = {}
        if "POST" in formats:
            item = ContentItem(content_type="POST", status="DRAFT", platforms=["FB", "Li", "X"], generated_content={"trend_title": trend_title})
            db.add(item)
            draft_items["POST"] = item
        if "CAROUSEL" in formats:
            item = ContentItem(content_type="CAROUSEL", status="DRAFT", platforms=["IG", "Li"], generated_content={"trend_title": trend_title})
            db.add(item)
            draft_items["CAROUSEL"] = item
        if "VIDEO_SCRIPT" in formats:
            item = ContentItem(content_type="VIDEO_SCRIPT", status="DRAFT", platforms=["TT", "IG"], generated_content={"trend_title": trend_title})
            db.add(item)
            draft_items["VIDEO_SCRIPT"] = item
        
        db.commit()
        
        text_to_process = f"Trend: {trend_title}\n\nContext/News: {trend_snippet}"
        carousel_platforms = ["IG", "Li"]
        generated = generate_selected_content(
            trend_title, text_to_process, formats,
            platforms=carousel_platforms
        )
        
        if not generated:
            logger.error("AI Generation failed for trend.")
            for item in draft_items.values():
                db.delete(item)
            db.commit()
            return
            
        if "posts" in generated and generated["posts"] and "POST" in draft_items:
            generated["posts"]["trend_title"] = trend_title
            draft_items["POST"].generated_content = generated["posts"]
            draft_items["POST"].status = "pending_review"
        elif "POST" in draft_items:
            db.delete(draft_items["POST"])
            
        if "carousel" in generated and generated["carousel"] and "CAROUSEL" in draft_items:
            generated["carousel"]["trend_title"] = trend_title
            draft_items["CAROUSEL"].generated_content = generated["carousel"]
            draft_items["CAROUSEL"].status = "pending_review"
        elif "CAROUSEL" in draft_items:
            db.delete(draft_items["CAROUSEL"])
            
        if "video_script" in generated and generated["video_script"] and "VIDEO_SCRIPT" in draft_items:
            generated["video_script"]["trend_title"] = trend_title
            draft_items["VIDEO_SCRIPT"].generated_content = generated["video_script"]
            draft_items["VIDEO_SCRIPT"].status = "pending_review"
        elif "VIDEO_SCRIPT" in draft_items:
            db.delete(draft_items["VIDEO_SCRIPT"])
            
        db.commit()
        logger.info(f"Trend generation completed for: {trend_title}")

    except Exception as e:
        logger.error(f"Failed to generate trend content: {e}")
        # Cleanup drafts on exception
        if 'draft_items' in locals():
            for item in draft_items.values():
                db.delete(item)
            db.commit()
    finally:
        db.close()
