"""
Video API Router — render content items as slideshow MP4 videos
"""
import concurrent.futures
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.content_item import ContentItem
from app.services.video_renderer import render_video_sync, content_item_to_slides

logger = logging.getLogger(__name__)
router = APIRouter()

_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
_render_status: dict = {}

VIDEO_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "static" / "video_output"


def _do_render(content_item_id: int, slides: list, brand: str):
    _render_status[content_item_id] = "rendering"
    try:
        url = render_video_sync(slides, content_item_id, brand=brand)
        _render_status[content_item_id] = {"status": "done", "url": url}
        logger.info(f"Video rendered for {content_item_id}: {url}")
    except Exception as e:
        _render_status[content_item_id] = {"status": "error", "error": str(e)}
        logger.error(f"Video render failed for {content_item_id}: {e}", exc_info=True)


@router.post("/{content_item_id}/render")
async def render_video_endpoint(
    content_item_id: int,
    db: Session = Depends(get_db),
):
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

    # Get article metadata from related raw_article
    article_title = ""
    image_url = ""
    brand = "غرفة المحتوى"

    try:
        raw = item.raw_article  # relationship
        if raw:
            article_title = (raw.title or "")[:120]
            image_url = raw.image_url or ""
            source = raw.source_name or ""
            if source:
                brand = source
    except Exception:
        pass

    slides = content_item_to_slides(
        gen or {},
        item.content_type or "POST",
        brand=brand,
        article_title=article_title,
        image_url=image_url,
    )
    if not slides:
        raise HTTPException(status_code=400, detail="No slides could be extracted")

    _render_status[content_item_id] = "queued"
    _thread_pool.submit(_do_render, content_item_id, slides, brand)

    return {
        "detail": f"Video render started ({len(slides)} slides)",
        "slides_count": len(slides),
        "poll_url": f"/api/video/{content_item_id}/status",
    }


@router.get("/{content_item_id}/status")
async def get_render_status(content_item_id: int):
    status = _render_status.get(content_item_id)
    if status is None:
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
