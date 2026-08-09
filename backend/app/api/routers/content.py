from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
import os

from app.api.deps import get_db
from app.models.content_item import ContentItem
from app.schemas.content_item import ContentItemResponse, ContentItemUpdate

router = APIRouter()

CAROUSEL_OUTPUT = Path(__file__).parent.parent.parent.parent / "static" / "carousel_output"


@router.get("/", response_model=List[ContentItemResponse])
def get_all_content(db: Session = Depends(get_db)):
    items = db.query(ContentItem).order_by(ContentItem.created_at.desc()).all()
    return items

@router.get("/review", response_model=List[ContentItemResponse])
def get_content_for_review(db: Session = Depends(get_db)):
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
from typing import List, Optional, Any
from app.services.social.instagram import InstagramService
from app.services.social.facebook import FacebookService
from app.services.social.threads_service import ThreadsService

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
    
    if (is_ig or is_fb or is_th) and item.generated_content:
        # Check IG
        ig_published = False
        if is_ig:
            ig_service = InstagramService()
            if ig_service._is_configured():
                gen = item.generated_content
                caption = gen.get("instagram_caption", gen.get("title", ""))
                if item.content_type == "CAROUSEL" and "carousel_urls" in gen:
                    urls = gen["carousel_urls"]
                    if urls:
                        res = await ig_service.publish_carousel(urls, caption)
                        if not res.get("success"):
                            raise HTTPException(status_code=400, detail=f"IG: {res}")
                        ig_published = True
                elif item.content_type == "POST" and "image_url" in gen:
                    res = await ig_service.publish_image(gen["image_url"], caption)
                    if not res.get("success"):
                        raise HTTPException(status_code=400, detail=f"IG: {res}")
                    ig_published = True

        # Check FB
        fb_published = False
        if is_fb:
            fb_service = FacebookService()
            if fb_service._is_configured():
                gen = item.generated_content
                caption = gen.get("facebook_post", gen.get("title", ""))
                if item.content_type == "CAROUSEL" and "carousel_urls" in gen:
                    urls = gen["carousel_urls"]
                    if urls:
                        res = await fb_service.publish_carousel(urls, caption)
                        if not res.get("success"):
                            raise HTTPException(status_code=400, detail=f"FB: {res}")
                        fb_published = True
                elif item.content_type == "POST":
                    if "image_url" in gen and gen["image_url"]:
                        res = await fb_service.publish_image(gen["image_url"], caption)
                    else:
                        res = await fb_service.publish_text(caption)
                    
                    if not res.get("success"):
                        raise HTTPException(status_code=400, detail=f"FB: {res}")
                    fb_published = True

        if ig_published or fb_published:
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

    output_urls = render_carousel_sync(item_id, carousel_data, template_id, "zayedtech", custom_text_color, custom_accent_color)
    
    db = SessionLocal()
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if item:
        # generated_content is a dict, but modifying it directly might not trigger SQLAlchemy update
        new_content = copy.deepcopy(item.generated_content)
        if isinstance(new_content, str):
            import json
            new_content = json.loads(new_content)
            
        new_content["carousel_urls"] = output_urls
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
