from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
from pydantic import BaseModel
import os
import copy
import re
from sqlalchemy.orm.attributes import flag_modified
from ai_service.agents.base_agent import AgentClient, AgentConfig
import logging
logger = logging.getLogger(__name__)

from app.api.deps import get_db
from app.models.content_item import ContentItem
from app.schemas.content_item import ContentItemResponse, ContentItemUpdate

router = APIRouter()

CAROUSEL_OUTPUT = Path(__file__).parent.parent.parent.parent / "static" / "carousel_output"


@router.get("/", response_model=List[ContentItemResponse])
def get_all_content(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(hours=24)
    # Expire old pending content
    db.query(ContentItem).filter(
        ContentItem.status == "pending_review",
        ContentItem.created_at < cutoff
    ).update({"status": "EXPIRED"}, synchronize_session=False)
    db.commit()
    
    items = db.query(ContentItem).order_by(ContentItem.created_at.desc()).all()
    return items

@router.get("/review", response_model=List[ContentItemResponse])
def get_content_for_review(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(hours=24)
    # Expire old pending content
    db.query(ContentItem).filter(
        ContentItem.status == "pending_review",
        ContentItem.created_at < cutoff
    ).update({"status": "EXPIRED"}, synchronize_session=False)
    db.commit()

    items = db.query(ContentItem).filter(ContentItem.status == "pending_review").all()
    return items

@router.get("/scheduled", response_model=List[ContentItemResponse])
def get_scheduled_content(db: Session = Depends(get_db)):
    items = db.query(ContentItem).filter(ContentItem.status == "SCHEDULED").all()
    return items

from app.schemas.content_item import ContentItemUpdate

@router.put("/{item_id}", response_model=ContentItemResponse)
def update_content(item_id: int, content_update: ContentItemUpdate, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    item.generated_content = content_update.generated_content
    db.commit()
    db.refresh(item)
    return item
from typing import List, Optional, Any
from app.services.social.instagram import InstagramService
from app.services.social.facebook import FacebookService
from app.models.oauth_token import OAuthToken
from app.services.social.threads_service import ThreadsService
from app.services.social.linkedin_service import LinkedInService

def _ensure_english_linkedin(item: ContentItem):
    """Translate linkedin_post and carousel slides to English if they contain Arabic."""
    if not item.generated_content:
        return
    gen = item.generated_content
    if isinstance(gen, str):
        import json
        try:
            gen = json.loads(gen)
        except:
            return
    
    import re, copy
    from app.core.config import settings
    changed = False
    new_content = copy.deepcopy(gen)
    client = AgentClient(api_key=settings.ANTHROPIC_API_KEY)
    config = AgentConfig(
        name="Translator",
        role="Professional translator",
        goal="Translate text to English",
        backstory="Expert at translating social media posts to professional English."
    )

    # linkedin_post is now generated directly in English by Claude — no translation needed.
    # Just verify it's not Arabic (safety net).
    caption = gen.get("linkedin_post", "")
    if caption and re.search(r"[\u0600-\u06FF]", caption):
        translated = client.execute_task(config, f"Translate the following LinkedIn post to professional English. Return ONLY the English translation without quotes or introductory text:\n\n{caption}")
        new_content["linkedin_post"] = translated.strip()
        changed = True

    # 2. Translate carousel slides if they contain Arabic → store as linkedin_slides
    slides = gen.get("slides", [])
    if slides and item.content_type == "CAROUSEL":
        has_arabic = any(
            re.search(r"[\u0600-\u06FF]", str(s.get("heading", "")) + str(s.get("body", "")))
            for s in slides
        )
        if has_arabic:
            english_slides = []
            for slide in slides:
                en_slide = {}
                for field in ["heading", "body"]:
                    val = slide.get(field, "")
                    if val and re.search(r"[\u0600-\u06FF]", val):
                        translated = client.execute_task(config, f"Translate to professional English. Return ONLY the translation:\n\n{val}")
                        en_slide[field] = translated.strip()
                    else:
                        en_slide[field] = val
                # Translate tips_list if present
                tips = slide.get("tips_list")
                if tips:
                    en_tips = []
                    for tip in tips:
                        if re.search(r"[\u0600-\u06FF]", tip):
                            t = client.execute_task(config, f"Translate to professional English. Return ONLY the translation:\n\n{tip}")
                            en_tips.append(t.strip())
                        else:
                            en_tips.append(tip)
                    en_slide["tips_list"] = en_tips
                # Translate column fields if present
                for col_field in ["left_column_title", "right_column_title"]:
                    val = slide.get(col_field)
                    if val and re.search(r"[\u0600-\u06FF]", val):
                        t = client.execute_task(config, f"Translate to professional English. Return ONLY the translation:\n\n{val}")
                        en_slide[col_field] = t.strip()
                    elif val:
                        en_slide[col_field] = val
                for col_field in ["left_column_items", "right_column_items"]:
                    items_list = slide.get(col_field)
                    if items_list:
                        en_items = []
                        for it in items_list:
                            if re.search(r"[\u0600-\u06FF]", it):
                                t = client.execute_task(config, f"Translate to professional English. Return ONLY the translation:\n\n{it}")
                                en_items.append(t.strip())
                            else:
                                en_items.append(it)
                        en_slide[col_field] = en_items
                english_slides.append(en_slide)
            # Store English slides separately — arabic slides stay for other platforms
            new_content["linkedin_slides"] = english_slides
            # Clear any old linkedin carousel urls so they get re-rendered
            new_content.pop("linkedin_carousel_urls", None)
            changed = True

    if changed:
        item.generated_content = new_content
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(item, "generated_content")

class ApproveRequest(BaseModel):
    platforms: Optional[List[str]] = None

@router.post("/{item_id}/approve", response_model=ContentItemResponse)
async def approve_content(item_id: int, req: ApproveRequest = None, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
        
    if req and req.platforms is not None:
        item.platforms = req.platforms
        
    platforms = item.platforms or []
    if isinstance(platforms, str):
        platforms = platforms.split(",")
    is_ig = any("IG" in p.upper() or "INSTAGRAM" in p.upper() for p in platforms)
    is_fb = any("FB" in p.upper() or "FACEBOOK" in p.upper() for p in platforms)
    is_th = any("TH" in p.upper() or "THREADS" in p.upper() for p in platforms)
    is_tw = any("TW" in p.upper() or "X" in p.upper() or "TWITTER" in p.upper() for p in platforms)
    is_li = any("LI" in p.upper() or "LINKEDIN" in p.upper() for p in platforms)
    is_sc = any("SC" in p.upper() or "SNAPCHAT" in p.upper() for p in platforms)
    
    if is_li:
        _ensure_english_linkedin(item)
        db.commit()
        db.refresh(item)
    
    if (is_ig or is_fb or is_th or is_li or is_sc or is_tw) and item.generated_content:
        # Check IG
        ig_published = False
        if is_ig:
            ig_service = InstagramService()
            if ig_service._is_configured():
                gen = item.generated_content
                # Instagram: use unified_post as caption
                caption = gen.get("unified_post", gen.get("instagram_caption", gen.get("title", "")))
                if item.content_type == "CAROUSEL" and "carousel_urls" in gen:
                    urls = gen["carousel_urls"]
                    if urls:
                        res = await ig_service.publish_carousel(urls, caption)
                        if not res.get("success"):
                            raise HTTPException(status_code=400, detail=f"IG: {res}")
                        ig_published = True
                elif item.content_type == "POST":
                    # Use generated image_url or fall back to raw article image
                    img_url = gen.get("image_url") or (item.raw_article.image_url if item.raw_article else None)
                    if img_url:
                        res = await ig_service.publish_image(img_url, caption)
                        if not res.get("success"):
                            raise HTTPException(status_code=400, detail=f"IG: {res}")
                        ig_published = True

        # Check FB
        fb_published = False
        if is_fb:
            fb_service = FacebookService()
            if fb_service._is_configured():
                gen = item.generated_content
                # Facebook: use unified_post as caption
                caption = gen.get("unified_post", gen.get("facebook_post", gen.get("title", "")))
                if item.content_type == "CAROUSEL" and "carousel_urls" in gen:
                    urls = gen["carousel_urls"]
                    if urls:
                        res = await fb_service.publish_carousel(urls, caption)
                        if not res.get("success"):
                            raise HTTPException(status_code=400, detail=f"FB: {res}")
                        fb_published = True
                elif item.content_type == "POST":
                    # Use generated image_url or fall back to raw article image
                    img_url = gen.get("image_url") or (item.raw_article.image_url if item.raw_article else None)
                    if img_url:
                        res = await fb_service.publish_image(img_url, caption)
                    else:
                        res = await fb_service.publish_text(caption)
                    if not res.get("success"):
                        raise HTTPException(status_code=400, detail=f"FB: {res}")
                    fb_published = True

        # Check Threads
        th_published = False
        if is_th:
            th_service = ThreadsService()
            status = th_service.get_status(db)
            if status.get("connected"):
                gen = item.generated_content
                # X/Threads: use unified_post (truncate if needed)
                caption = gen.get("unified_post", gen.get("x_tweet", gen.get("title", "")))
                
                # Truncate to 500 characters just in case, since Threads API strictly fails over 500
                if len(caption) > 500:
                    caption = caption[:497] + "..."
                    
                access_token = await th_service.check_and_refresh_token(db)
                if access_token and status.get("account_id"):
                    img_url = gen.get("image_url") or (item.raw_article.image_url if item.raw_article and item.content_type == "POST" else None)
                    if img_url:
                        res = await th_service.publish_with_image(caption, img_url, access_token, status.get("account_id"))
                        if not res or not res.get("success"):
                            # Fallback to text if image publish fails
                            res = await th_service.publish_text(caption, access_token, status.get("account_id"))
                    else:
                        res = await th_service.publish_text(caption, access_token, status.get("account_id"))
                    if not res.get("success"):
                        raise HTTPException(status_code=400, detail=f"Threads: {res}")
                    th_published = True

        # Check Twitter (X)
        tw_published = False
        if is_tw:
            from app.services.social.twitter_service import TwitterService
            tw_service = TwitterService()
            if tw_service._is_configured():
                gen = item.generated_content
                # X (Twitter): use unified_post
                caption = gen.get("unified_post", gen.get("x_tweet", gen.get("title", "")))
                
                # X limits to 280 chars
                if len(caption) > 280:
                    caption = caption[:277] + "..."
                    
                # Twitter service is sync (tweepy), but we can call it here since it's fast
                img_url = gen.get("image_url") or (item.raw_article.image_url if item.raw_article and item.content_type == "POST" else None)
                if img_url:
                    res = tw_service.publish_with_image(caption, img_url)
                    if not res or not res.get("success"):
                        res = tw_service.publish_text(caption)
                else:
                    res = tw_service.publish_text(caption)
                if not res.get("success"):
                    raise HTTPException(status_code=400, detail=f"X/Twitter: {res}")
                tw_published = True

        # Check LinkedIn
        li_published = False
        if is_li:
            li_service = LinkedInService()
            status = li_service.get_status(db)
            if status.get("connected"):
                gen = item.generated_content
                caption = gen.get("linkedin_post", gen.get("title", ""))
                
                access_token = token_entry.access_token if (token_entry := db.query(OAuthToken).filter(OAuthToken.platform == "linkedin").first()) else None
                if access_token and status.get("account_id"):
                    res = None
                    # Prefer English-rendered carousel for LinkedIn
                    li_carousel_urls = gen.get("linkedin_carousel_urls", [])
                    carousel_urls = li_carousel_urls if li_carousel_urls else gen.get("carousel_urls", [])
                    
                    # If we have linkedin_slides (English) but no linkedin_carousel_urls yet → render them now
                    if not li_carousel_urls and gen.get("linkedin_slides") and item.content_type == "CAROUSEL":
                        try:
                            from app.services.carousel_renderer import render_carousel_sync
                            import copy as _copy
                            li_data = _copy.deepcopy(gen)
                            li_data["slides"] = gen["linkedin_slides"]
                            li_data["title"] = gen.get("title", "")
                            li_urls = render_carousel_sync(item.id, li_data, None, "zayedtech", None, None)
                            # Store for future use
                            import copy as _copy2
                            new_gen = _copy2.deepcopy(item.generated_content)
                            new_gen["linkedin_carousel_urls"] = li_urls
                            item.generated_content = new_gen
                            from sqlalchemy.orm.attributes import flag_modified
                            flag_modified(item, "generated_content")
                            db.commit()
                            carousel_urls = li_urls
                        except Exception as e:
                            logger.error(f"Failed to render English LinkedIn carousel: {e}")
                    
                    if carousel_urls and isinstance(carousel_urls, list) and len(carousel_urls) > 0:
                        import tempfile, os as _os, httpx as _httpx
                        from PIL import Image as _Image
                        from io import BytesIO as _BytesIO
                        images = []
                        for img_url in carousel_urls:
                            try:
                                resp = _httpx.get(img_url, timeout=30.0)
                                if resp.status_code == 200:
                                    img = _Image.open(_BytesIO(resp.content)).convert('RGB')
                                    images.append(img)
                            except Exception as e:
                                logger.error(f"Failed to download carousel image {img_url}: {e}")
                        if images:
                            with tempfile.TemporaryDirectory() as tmpdirname:
                                img_paths = []
                                for i, img in enumerate(images):
                                    path = _os.path.join(tmpdirname, f"slide_{i}.jpg")
                                    img.save(path, format="JPEG")
                                    img_paths.append(path)
                                res = await li_service.publish_media(caption, img_paths, "IMAGE", access_token, status.get("account_id"))
                    elif item.raw_article and item.raw_article.image_url:
                        import tempfile, os as _os, httpx as _httpx
                        try:
                            resp = _httpx.get(item.raw_article.image_url, timeout=30.0)
                            if resp.status_code == 200:
                                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                                    temp_img_path = f.name
                                    f.write(resp.content)
                                res = await li_service.publish_media(caption, [temp_img_path], "IMAGE", access_token, status.get("account_id"))
                                _os.remove(temp_img_path)
                        except Exception as e:
                            logger.error(f"Failed to download cover image for LinkedIn: {e}")
                    if not res:
                        res = await li_service.publish_text(caption, access_token, status.get("account_id"))
                    if not res.get("success"):
                        raise HTTPException(status_code=400, detail=f"LinkedIn: {res}")
                    li_published = True

        # Check Snapchat
        sc_published = False
        if is_sc:
            from app.services.social.snapchat_service import SnapchatService
            sc_service = SnapchatService()
            status = sc_service.get_status(db)
            if status.get("connected"):
                gen = item.generated_content
                caption = gen.get("instagram_post", gen.get("title", "")) # Fallback to IG text or Title
                
                # We expect the media_url to be either a carousel or a video
                media_url = item.carousel_url or item.video_url
                media_type = "VIDEO" if item.video_url else "IMAGE"
                
                # If it's a carousel but the url is stored in generated_content
                if not media_url and "carousel_urls" in gen and gen["carousel_urls"]:
                    media_url = gen["carousel_urls"][0] # Take first slide
                    media_type = "IMAGE"

                if not media_url:
                    raise HTTPException(status_code=400, detail="Snapchat requires a video or a carousel (image) URL")
                
                res = await sc_service.publish_media(db, media_url, caption, media_type)
                if not res.get("success"):
                    raise HTTPException(status_code=400, detail=f"Snapchat: {res}")
                sc_published = True

        if ig_published or fb_published or th_published or li_published or sc_published or tw_published:
            item.status = "PUBLISHED"
        else:
            item.status = "APPROVED"
    else:
        item.status = "APPROVED"
        
    db.commit()
    db.refresh(item)
    return item

class ScheduleRequest(BaseModel):
    scheduled_at: datetime
    platforms: Optional[List[str]] = None

@router.post("/{item_id}/schedule", response_model=ContentItemResponse)
def schedule_content(item_id: int, req: ScheduleRequest, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    item.status = "SCHEDULED"
    item.scheduled_at = req.scheduled_at
    if req.platforms is not None:
        item.platforms = req.platforms
        
    platforms = item.platforms or []
    if isinstance(platforms, str):
        platforms = platforms.split(",")
    is_li = any("LI" in p.upper() or "LINKEDIN" in p.upper() for p in platforms)
    if is_li:
        _ensure_english_linkedin(item)
        
    db.commit()
    db.refresh(item)
    return item

@router.post("/{item_id}/reject", response_model=ContentItemResponse)
def reject_content(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    item.status = "REJECTED"
    db.commit()
    db.refresh(item)
    return item

# ─── Carousel Image Rendering ────────────────────────────────────────────────

from typing import Optional

def _do_render(item_id: int, carousel_data: dict, template_id: Optional[int] = None, custom_text_color: Optional[str] = None, custom_accent_color: Optional[str] = None):
    from app.services.carousel_renderer import render_carousel_sync
    from app.db.session import SessionLocal
    from app.models.content_item import ContentItem
    import copy
    
    db = SessionLocal()
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        db.close()
        return

    new_content = copy.deepcopy(item.generated_content)
    if isinstance(new_content, str):
        import json
        new_content = json.loads(new_content)

    try:
        output_urls = render_carousel_sync(item_id, carousel_data, template_id, "zayedtech", custom_text_color, custom_accent_color)
        new_content["carousel_urls"] = output_urls
        new_content.pop("carousel_error", None) # Clear any previous error
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Carousel Render Error for item {item_id}: {error_msg}")
        traceback.print_exc()
        new_content["carousel_error"] = error_msg
        
    item.generated_content = new_content
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(item, "generated_content")
    
    db.commit()
    db.close()

@router.post("/{item_id}/render-carousel")
def render_carousel(
    item_id: int, 
    background_tasks: BackgroundTasks, 
    template_id: Optional[int] = None, 
    custom_text_color: Optional[str] = None,
    custom_accent_color: Optional[str] = None,
    db: Session = Depends(get_db)
):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    if item.content_type != "CAROUSEL":
        raise HTTPException(status_code=400, detail="Item is not a carousel")

    carousel_data = item.generated_content
    if isinstance(carousel_data, str):
        import json
        carousel_data = json.loads(carousel_data)

    import shutil
    slide_dir = CAROUSEL_OUTPUT / str(item_id)
    if slide_dir.exists():
        shutil.rmtree(slide_dir, ignore_errors=True)

    background_tasks.add_task(_do_render, item_id, carousel_data, template_id, custom_text_color, custom_accent_color)
    return {"detail": "Rendering started", "item_id": item_id}

@router.get("/{item_id}/carousel-slides")
def get_carousel_slides(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        return {"slides": [], "ready": False}
        
    expected_count = 0
    data = {}
    if item.content_type == "CAROUSEL" and item.generated_content:
        import json
        data = item.generated_content
        if isinstance(data, str):
            data = json.loads(data)
        expected_count = len(data.get("slides", []))

    carousel_urls = data.get("carousel_urls", [])
    carousel_error = data.get("carousel_error")
    
    if carousel_error:
        return {"slides": [], "ready": True, "error": carousel_error, "count": 0}
        
    is_ready = len(carousel_urls) >= expected_count if expected_count > 0 else len(carousel_urls) > 0
    
    return {"slides": carousel_urls, "ready": is_ready, "count": len(carousel_urls)}

@router.delete("/{item_id}/carousel-slides")
def delete_carousel_slides(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
        
    data = item.generated_content
    if isinstance(data, str):
        import json
        data = json.loads(data)
        
    if isinstance(data, dict):
        # Delete from Cloudinary
        try:
            import cloudinary.api
            cloudinary.api.delete_resources_by_prefix(f"carousel_output/{item_id}")
        except Exception as e:
            print("Failed to delete from Cloudinary:", e)
            
        import copy
        new_content = copy.deepcopy(data)
        new_content["carousel_urls"] = []
        item.generated_content = new_content
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(item, "generated_content")
        db.commit()
        
    return {"detail": "Carousel deleted successfully"}
