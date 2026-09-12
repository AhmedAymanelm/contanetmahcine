import logging
from sqlalchemy.orm import Session
from app.models.raw_article import RawArticle
from app.models.content_item import ContentItem
from ai_service.generation_pipeline import generate_selected_content
from app.services.carousel_renderer import render_carousel_sync
from app.core.config import settings

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

def process_article_generation(raw_article_id: int, formats: list = None, carousel_platforms: list = None):
    """
    Takes a RawArticle ID, sends it to Claude for generation,
    saves the results as ContentItems, and updates status.
    """
    if formats is None:
        formats = ["POST", "CAROUSEL", "VIDEO_SCRIPT"]
    if carousel_platforms is None:
        carousel_platforms = ["IG", "Li"]
        
    db = SessionLocal()
    try:
        article = db.query(RawArticle).filter(RawArticle.id == raw_article_id).first()
        if not article:
            logger.error(f"Article {raw_article_id} not found for generation.")
            return

        # Call AI pipeline - POST + VIDEO only first (carousel handled separately below)
        formats_no_carousel = [f for f in formats if f != "CAROUSEL"]
        text_to_process = article.content if article.content else article.title
        generated = generate_selected_content(
            api_key=settings.ANTHROPIC_API_KEY,
            title=article.title, 
            content=text_to_process, 
            formats=formats_no_carousel,
            platforms=carousel_platforms
        ) if formats_no_carousel else {}
        
        # Only fail if we expected non-carousel content but got nothing
        if not generated and formats_no_carousel:
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
                    platforms=["FB", "X"],
                    generated_content=generated["posts"]
                )
            )
            
        # 2. Carousels - Generate BOTH Arabic (IG) and English (LinkedIn)
        if "CAROUSEL" in formats:
            from ai_service.generation_pipeline import generate_carousel as _gen_carousel
            
            # Arabic carousel for Instagram
            try:
                ig_carousel = _gen_carousel(
                    api_key=settings.ANTHROPIC_API_KEY,
                    article_title=article.title,
                    article_content=text_to_process,
                    platforms=["IG"]
                )
                if ig_carousel and "slides" in ig_carousel:
                    ig_item = ContentItem(
                        raw_article_id=article.id,
                        content_type="CAROUSEL",
                        status="pending_review",
                        platforms=["IG"],
                        generated_content=ig_carousel
                    )
                    db.add(ig_item)
                    db.flush()
                    try:
                        render_carousel_sync(ig_item.id, ig_carousel)
                    except Exception as render_err:
                        logger.warning(f"IG Carousel rendering failed: {render_err}")
                    logger.info(f"Generated Arabic (IG) carousel for article {article.id}")
            except Exception as ig_err:
                logger.error(f"Arabic carousel generation failed: {ig_err}")
            
            # English carousel for LinkedIn
            try:
                li_carousel = _gen_carousel(
                    api_key=settings.ANTHROPIC_API_KEY,
                    article_title=article.title,
                    article_content=text_to_process,
                    platforms=["Li"]
                )
                if li_carousel and "slides" in li_carousel:
                    li_item = ContentItem(
                        raw_article_id=article.id,
                        content_type="CAROUSEL",
                        status="pending_review",
                        platforms=["Li"],
                        generated_content=li_carousel
                    )
                    db.add(li_item)
                    db.flush()
                    try:
                        render_carousel_sync(li_item.id, li_carousel)
                    except Exception as render_err:
                        logger.warning(f"Li Carousel rendering failed: {render_err}")
                    logger.info(f"Generated English (LinkedIn) carousel for article {article.id}")
            except Exception as li_err:
                logger.error(f"LinkedIn carousel generation failed: {li_err}")
            
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
            
        # Commit items_to_add (POST, VIDEO) and mark article as generated
        # (Carousel items are already flushed/committed individually above)
        any_carousel = "CAROUSEL" in formats
        if items_to_add:
            for item in items_to_add:
                if item not in db.new:
                    db.add(item)
            article.status = "GENERATED"
            db.commit()
            logger.info(f"Successfully generated content items for article {article.id}")
        elif any_carousel:
            # Only carousels were selected — mark as generated anyway
            article.status = "GENERATED"
            db.commit()
            logger.info(f"Carousel-only generation done for article {article.id}")
        else:
            logger.error(f"Claude returned empty content for article {article.id}. Status not updated.")
            # Leave it as PENDING or change to a failed state so it can be retried
            article.status = "PENDING"
            db.commit()
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        db.rollback()
        try:
            # Reset status on failure so it can be retried
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
            item = ContentItem(content_type="POST", status="DRAFT", platforms=["FB", "X"], generated_content={"trend_title": trend_title})
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
            api_key=settings.ANTHROPIC_API_KEY,
            title=trend_title, 
            content=text_to_process, 
            formats=formats,
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
            
            # Render images
            if "slides" in generated["carousel"]:
                render_carousel_sync(draft_items["CAROUSEL"].id, generated["carousel"])
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
