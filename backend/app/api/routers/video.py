"""
Video API Router — render content items as slideshow MP4 videos
"""
import concurrent.futures
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.content_item import ContentItem
from app.models.visual_template import VisualTemplate
from app.services.video_renderer import render_video_sync, content_item_to_slides

logger = logging.getLogger(__name__)
router = APIRouter()

_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# Track in-progress renders {content_item_id: status}
_render_status: dict = {}

VIDEO_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "static" / "video_output"


class VideoRenderRequest(BaseModel):
    template_id: Optional[Union[int, str]] = None
    template_name: Optional[str] = None
    custom_colors: Optional[Dict[str, Any]] = None
    slides_deck: Optional[List[Dict[str, Any]]] = None
    slides_json: Optional[str] = None
    show_ministry_logo: Optional[bool] = None
    brand_mode: Optional[str] = "ministry"  # "ministry" or "client"


def _do_render(content_item_id: int, slides: list, brand: str, brand_mode: str = "ministry"):
    """Background task: runs the render and updates status dict."""
    _render_status[content_item_id] = {"status": "rendering", "brand_mode": brand_mode}
    try:
        url = render_video_sync(slides, content_item_id, brand=brand)
        _render_status[content_item_id] = {"status": "done", "url": url, "brand_mode": brand_mode}
        logger.info(f"Video rendered for content item {content_item_id} ({brand_mode}): {url}")
    except Exception as e:
        _render_status[content_item_id] = {"status": "error", "error": str(e), "brand_mode": brand_mode}
        logger.error(f"Video render failed for content item {content_item_id}: {e}")


@router.post("/{content_item_id}/render")
async def render_video_endpoint(
    content_item_id: int,
    template_id: Optional[Union[int, str]] = None,
    show_ministry_logo: bool = True,
    body: Optional[VideoRenderRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Start rendering a content item as a slideshow video with optional visual template styling.
    Returns immediately — poll /status to check progress.
    """
    item = db.query(ContentItem).filter(ContentItem.id == content_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")

    if body:
        if body.template_id is not None:
            template_id = body.template_id
        if body.show_ministry_logo is not None:
            show_ministry_logo = body.show_ministry_logo

    brand_mode = "ministry"
    if body and body.brand_mode:
        brand_mode = body.brand_mode.strip().lower()
    elif body and body.show_ministry_logo is not None:
        brand_mode = "ministry" if body.show_ministry_logo else "client"
    elif not show_ministry_logo:
        brand_mode = "client"

    show_ministry_logo = (brand_mode == "ministry")

    gen = item.generated_content
    if isinstance(gen, str):
        try:
            gen = json.loads(gen)
        except Exception:
            gen = {}

    raw_art = item.raw_article
    art_title = raw_art.title if raw_art else ""
    art_img = raw_art.image_url if raw_art else ""

    brand = "zayedtech"
    author_name = "د. زايد الحميري"

    try:
        slides = content_item_to_slides(
            gen or {},
            item.content_type or "POST",
            brand=brand,
            author_name=author_name,
            article_title="" if (item.content_type in ("REEL", "VIDEO_SCRIPT")) else art_title,
            image_url=art_img,
            brand_mode=brand_mode,
        )
    except Exception as e:
        logger.error(f"Error extracting slides for content item {content_item_id}: {e}")
        slides = []

    if not slides:
        raise HTTPException(status_code=400, detail="لا يمكن استخراج شرائح فيديو من هذا الخبر")

    for sl in slides:
        sl["brand_mode"] = brand_mode
        sl["show_ministry_logo"] = show_ministry_logo

    # Resolve template styling
    tpl_name = (body.template_name if body and body.template_name else None) or "الافتراضي"
    tpl_deck: List[Dict[str, Any]] = []

    # 1. Direct deck from request body
    if body and body.slides_deck:
        tpl_deck = body.slides_deck
    elif body and body.slides_json:
        try:
            tpl_deck = json.loads(body.slides_json)
        except Exception:
            pass

    # 2. Database lookup if template_id is provided and deck not yet set
    if template_id and not tpl_deck:
        try:
            tid = int(template_id)
            tpl = db.query(VisualTemplate).filter(VisualTemplate.id == tid).first()
            if tpl:
                tpl_name = tpl.name or tpl_name
                if getattr(tpl, "slides_json", None):
                    try:
                        tpl_deck = json.loads(tpl.slides_json)
                    except Exception:
                        pass
                if not tpl_deck:
                    tpl_deck = [{
                        "accent": getattr(tpl, "accent_color", None) or "#FF5C00",
                        "color1": getattr(tpl, "bg_color1", None) or "#0a0a0a",
                        "color2": getattr(tpl, "bg_color2", None) or "#1a0a00",
                        "text_color": getattr(tpl, "text_color", None) or "#ffffff",
                    }]
        except Exception as tpl_err:
            logger.warning(f"Could not load visual template {template_id} from DB: {tpl_err}")

    # 3. Direct custom_colors from request body
    if body and body.custom_colors and not tpl_deck:
        tpl_deck = [body.custom_colors]

    # Apply template colors to each slide
    if tpl_deck:
        for i, sl in enumerate(slides):
            cfg = tpl_deck[i % len(tpl_deck)]
            sl["custom_colors"] = {
                "accent": cfg.get("accentColor") or cfg.get("accent_color") or cfg.get("accent") or "#FF5C00",
                "color1": cfg.get("color1") or cfg.get("bg_color1") or "#0a0a0a",
                "color2": cfg.get("color2") or cfg.get("bg_color2") or "#1a0a00",
                "text_color": cfg.get("textColor") or cfg.get("text_color") or "#ffffff",
            }

    # Submit background render
    _render_status[content_item_id] = {"status": "queued", "brand_mode": brand_mode}
    _thread_pool.submit(_do_render, content_item_id, slides, brand, brand_mode)

    brand_label = "وزارة تمكين المجتمع" if brand_mode == "ministry" else "العميل (د. زايد الحميري)"
    return {
        "detail": f"Video render started for content item {content_item_id} ({len(slides)} slides, هوية: {brand_label}, قالب: {tpl_name})",
        "slides_count": len(slides),
        "brand_mode": brand_mode,
        "template_id": template_id,
        "poll_url": f"/api/video/{content_item_id}/status",
    }


@router.get("/{content_item_id}/status")
async def get_render_status(content_item_id: int):
    """
    Poll the render status for a content item.
    Returns: queued | rendering | done (with url, brand_mode) | error
    """
    status = _render_status.get(content_item_id)
    if status is None:
        # Check if a video file already exists for this item
        existing = list(VIDEO_OUTPUT_DIR.glob(f"video_{content_item_id}_*.mp4"))
        if existing:
            latest = max(existing, key=lambda p: p.stat().st_mtime)
            brand_mode = "ministry"
            meta_path = VIDEO_OUTPUT_DIR / (latest.name + ".json")
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as mf:
                        meta_data = json.load(mf)
                        brand_mode = meta_data.get("brand_mode", "ministry")
                except Exception:
                    pass
            return {
                "status": "done",
                "url": f"/static/video_output/{latest.name}",
                "content_item_id": content_item_id,
                "brand_mode": brand_mode,
            }
        return {"status": "not_started", "content_item_id": content_item_id}

    if isinstance(status, str):
        return {"status": status, "content_item_id": content_item_id}

    return {"content_item_id": content_item_id, **status}

