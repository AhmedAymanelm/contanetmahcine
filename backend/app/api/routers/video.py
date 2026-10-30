"""
Video API Router — render content items as slideshow MP4 videos
"""
import concurrent.futures
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.content_item import ContentItem
from app.services.video_renderer import render_video_sync, content_item_to_slides

logger = logging.getLogger(__name__)
router = APIRouter()

_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# Track in-progress renders {content_item_id: status}
_render_status: dict = {}

VIDEO_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "static" / "video_output"


def _do_render(content_item_id: int, slides: list, brand: str):
    """Background task: runs the render and updates status dict."""
    _render_status[content_item_id] = "rendering"
    try:
        url = render_video_sync(slides, content_item_id, brand=brand)
        _render_status[content_item_id] = {"status": "done", "url": url}
        logger.info(f"Video rendered for content item {content_item_id}: {url}")
    except Exception as e:
        _render_status[content_item_id] = {"status": "error", "error": str(e)}
        logger.error(f"Video render failed for content item {content_item_id}: {e}")


@router.post("/{content_item_id}/render")
async def render_video_endpoint(
    content_item_id: int,
    db: Session = Depends(get_db),
):
    """
    Start rendering a content item as a slideshow video.
    Returns immediately — poll /status to check progress.
    """
    item = db.query(ContentItem).filter(ContentItem.id == content_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")

    gen = item.generated_content
    if isinstance(gen, str):
        import json
        try:
            gen = json.loads(gen)
        except Exception:
            gen = {}

    raw_art = item.raw_article
    art_title = raw_art.title if raw_art else ""
    art_img = raw_art.image_url if raw_art else ""

    brand = "zayedtech"
    author_name = "د. زايد الحميري"

    slides = content_item_to_slides(
        gen or {},
        item.content_type or "POST",
        brand=brand,
        author_name=author_name,
        article_title="" if (item.content_type in ("REEL", "VIDEO_SCRIPT")) else art_title,
        image_url=art_img,
    )
    if not slides:
        raise HTTPException(status_code=400, detail="No slides could be extracted from this content item")

    # Submit background render
    _render_status[content_item_id] = "queued"
    _thread_pool.submit(_do_render, content_item_id, slides, brand)

    return {
        "detail": f"Video render started for content item {content_item_id} ({len(slides)} slides)",
        "slides_count": len(slides),
        "poll_url": f"/api/video/{content_item_id}/status",
    }


@router.get("/{content_item_id}/status")
async def get_render_status(content_item_id: int):
    """
    Poll the render status for a content item.
    Returns: queued | rendering | done (with url) | error
    """
    status = _render_status.get(content_item_id)
    if status is None:
        # Check if a video file already exists for this item
        existing = list(VIDEO_OUTPUT_DIR.glob(f"video_{content_item_id}_*.mp4"))
        if existing:
            latest = max(existing, key=lambda p: p.stat().st_mtime)
            return {
                "status": "done",
                "url": f"/static/video_output/{latest.name}",
                "content_item_id": content_item_id,
            }
        return {"status": "not_started", "content_item_id": content_item_id}

    if isinstance(status, str):
        return {"status": status, "content_item_id": content_item_id}

    return {"content_item_id": content_item_id, **status}

