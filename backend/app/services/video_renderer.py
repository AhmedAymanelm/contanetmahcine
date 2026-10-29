"""
Video Renderer — Slideshow MP4 with slide transitions
Format: 1080×1920 (9:16 vertical — Reels/TikTok)
Style: Warm beige background, numbered slides, Arabic text, smooth slide-in transitions
"""

import asyncio
import os
import time
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from PIL import Image

OUTPUT_DIR = Path(__file__).parent.parent.parent / "static" / "video_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Slide icons by index
SLIDE_ICONS = ["📌", "🔥", "💡", "⚡", "🎯", "🚀", "📊", "🌟", "🔑", "✨"]


def _progress_dots_html(current: int, total: int) -> str:
    """Build progress dot indicators."""
    parts = []
    for i in range(total):
        is_active = (i + 1 == current)
        width = "28px" if is_active else "8px"
        bg = "#8b6f47" if is_active else "rgba(0,0,0,0.15)"
        parts.append(
            '<div style="width:' + width + ';height:8px;border-radius:4px;'
            'background:' + bg + ';transition:all .3s;"></div>'
        )
    return "".join(parts)


def _category_badge(category: str) -> str:
    if not category:
        return ""
    return (
        '<div style="background:#1a1a1a;color:#fff;padding:10px 28px;'
        'border-radius:50px;font-size:30px;font-weight:700;">' + category + "</div>"
    )


def _tool_badge(tool_name: str) -> str:
    if not tool_name:
        return ""
    return (
        '<div style="background:#c8a882;color:#fff;padding:10px 28px;'
        'border-radius:50px;font-size:28px;font-weight:700;">' + tool_name + "</div>"
    )


def _detail_box(detail: str) -> str:
    if not detail:
        return ""
    return (
        '<div style="background:rgba(0,0,0,0.06);border-radius:20px;'
        'padding:24px 32px;width:100%;text-align:right;">'
        '<span style="font-size:34px;font-weight:700;color:rgba(0,0,0,0.55);">'
        + detail
        + "</span></div>"
    )


def _slide_html(slide: dict, cairo_css: str) -> str:
    number  = slide.get("number", "01")
    icon    = slide.get("icon", "📌")
    category = slide.get("category", "")
    tool_name = slide.get("tool_name", "")
    headline  = slide.get("headline", "")
    detail    = slide.get("detail", "")
    total   = slide.get("total", 1)
    current = slide.get("current", 1)
    brand   = slide.get("brand", "غرفة المحتوى")

    dots_html     = _progress_dots_html(current, total)
    cat_badge     = _category_badge(category)
    tool_badge    = _tool_badge(tool_name)
    detail_html   = _detail_box(detail)

    return """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
""" + cairo_css + """
* { margin:0; padding:0; box-sizing:border-box; font-family:'Cairo',sans-serif; }
html, body { width:1080px; height:1920px; overflow:hidden; }
body {
    background: linear-gradient(160deg, #f5ede0 0%, #ede0cd 60%, #e8d5c0 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
}
</style>
</head>
<body>

  <!-- Top progress + label -->
  <div style="position:absolute;top:70px;right:60px;left:60px;
              display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;gap:10px;align-items:center;">""" + dots_html + """</div>
    <span style="font-size:32px;color:rgba(0,0,0,0.35);font-weight:600;">
      مهارة """ + str(current) + """ من """ + str(total) + """
    </span>
  </div>

  <!-- Main card -->
  <div style="width:860px;background:rgba(255,255,255,0.45);border-radius:40px;
              padding:70px 60px;
              box-shadow:0 20px 60px rgba(0,0,0,0.08);
              border:1px solid rgba(255,255,255,0.7);
              display:flex;flex-direction:column;align-items:flex-end;gap:28px;">

    <!-- Icon + Number -->
    <div style="display:flex;align-items:center;justify-content:space-between;width:100%;">
      <div style="font-size:200px;font-weight:900;color:#1a1a1a;line-height:1;
                  font-variant-numeric:tabular-nums;" dir="ltr">""" + number + """</div>
      <div style="width:110px;height:110px;background:rgba(0,0,0,0.08);
                  border-radius:28px;display:flex;align-items:center;
                  justify-content:center;font-size:54px;">""" + icon + """</div>
    </div>

    <!-- Badges -->
    <div style="display:flex;gap:14px;flex-wrap:wrap;justify-content:flex-end;">
      """ + cat_badge + tool_badge + """
    </div>

    <!-- Headline -->
    <div style="font-size:72px;font-weight:900;color:#1a1a1a;
                line-height:1.3;text-align:right;width:100%;">
      """ + headline + """
    </div>

    """ + detail_html + """

  </div>

  <!-- Footer -->
  <div style="position:absolute;bottom:60px;right:60px;left:60px;
              display:flex;justify-content:space-between;align-items:center;
              border-top:1px solid rgba(0,0,0,0.1);padding-top:28px;">
    <span style="font-size:30px;color:rgba(0,0,0,0.4);font-weight:600;">احفظه للروابط 🔖</span>
    <span style="font-size:30px;color:rgba(0,0,0,0.5);font-weight:700;">""" + brand + """</span>
  </div>

</body>
</html>"""


# ── Transition: horizontal slide-in from right ───────────────────────────────
def _make_slide_transition(
    img_a: Image.Image, img_b: Image.Image, n_frames: int = 15
) -> List[np.ndarray]:
    """Returns list of numpy arrays for a smooth horizontal slide transition."""
    frames = []
    w, h = img_a.width, img_a.height
    for i in range(n_frames):
        t = i / n_frames
        # ease-in-out cubic
        t = t * t * (3.0 - 2.0 * t)
        offset = int(w * t)
        combined = Image.new("RGB", (w, h))
        if offset < w:
            combined.paste(img_a.crop((offset, 0, w, h)), (0, 0))
        if offset > 0:
            combined.paste(img_b.crop((0, 0, offset, h)), (w - offset, 0))
        frames.append(np.array(combined))
    return frames


# ── Async slide PNG renderer ─────────────────────────────────────────────────
async def _render_slide_png(html: str, output_path: Path):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(path=str(output_path), full_page=False)
        await browser.close()


# ── Main async render ────────────────────────────────────────────────────────
async def render_video(
    slides_data: List[Dict[str, Any]],
    content_item_id: int,
    brand: str = "غرفة المحتوى",
    slide_duration: float = 3.0,
    fps: int = 30,
) -> str:
    """
    Renders a slideshow MP4 with slide-in transitions.
    Returns the static URL path to the rendered MP4.
    """
    from moviepy.editor import VideoClip

    try:
        from app.services.cairo_font_embedded import CAIRO_FONT_CSS
    except ImportError:
        CAIRO_FONT_CSS = ""

    total = len(slides_data)
    tmp_dir = OUTPUT_DIR / ("tmp_" + str(content_item_id) + "_" + str(int(time.time())))
    tmp_dir.mkdir(parents=True, exist_ok=True)

    slide_pngs: List[Path] = []

    # 1. Render each slide as PNG
    for idx, slide in enumerate(slides_data):
        slide["number"] = str(idx + 1).zfill(2)
        if not slide.get("icon"):
            slide["icon"] = SLIDE_ICONS[idx % len(SLIDE_ICONS)]
        slide["total"] = total
        slide["current"] = idx + 1
        slide["brand"] = brand

        html = _slide_html(slide, CAIRO_FONT_CSS)
        png_path = tmp_dir / ("slide_" + str(idx).zfill(2) + ".png")
        await _render_slide_png(html, png_path)
        slide_pngs.append(png_path)

    # 2. Load images
    images = [Image.open(str(p)).convert("RGB") for p in slide_pngs]

    # 3. Build all frames
    slide_frames_count = int(slide_duration * fps)
    transition_frame_count = 15  # 0.5s at 30fps

    all_frames: List[np.ndarray] = []

    for idx, img in enumerate(images):
        arr = np.array(img)
        all_frames.extend([arr] * slide_frames_count)

        if idx < len(images) - 1:
            transition = _make_slide_transition(img, images[idx + 1], transition_frame_count)
            all_frames.extend(transition)

    # 4. Write MP4
    timestamp = int(time.time())
    out_filename = "video_" + str(content_item_id) + "_" + str(timestamp) + ".mp4"
    out_path = OUTPUT_DIR / out_filename

    def make_frame(t):
        frame_idx = min(int(t * fps), len(all_frames) - 1)
        return all_frames[frame_idx]

    total_duration = len(all_frames) / fps
    clip = VideoClip(make_frame, duration=total_duration)
    clip.write_videofile(
        str(out_path),
        fps=fps,
        codec="libx264",
        audio=False,
        preset="fast",
        ffmpeg_params=["-crf", "23"],
        logger=None,
    )

    # Cleanup
    for p in slide_pngs:
        try:
            p.unlink()
        except Exception:
            pass
    try:
        tmp_dir.rmdir()
    except Exception:
        pass

    return "/static/video_output/" + out_filename


def render_video_sync(
    slides_data: List[Dict[str, Any]],
    content_item_id: int,
    brand: str = "غرفة المحتوى",
    slide_duration: float = 3.0,
    fps: int = 30,
) -> str:
    """Synchronous wrapper around render_video()."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            render_video(slides_data, content_item_id, brand, slide_duration, fps)
        )
    finally:
        loop.close()


# ── Content item → slides converter ─────────────────────────────────────────
def content_item_to_slides(
    generated_content: dict, content_type: str
) -> List[Dict[str, Any]]:
    """Converts a ContentItem's generated_content into slide dicts."""
    slides: List[Dict[str, Any]] = []

    if content_type == "VIDEO_SCRIPT":
        hook  = generated_content.get("hook", "")
        body  = generated_content.get("body", "")
        cta   = generated_content.get("call_to_action", "")
        cues  = generated_content.get("visual_cues", "")

        lines = [
            ln.strip().lstrip("-•* ").strip()
            for ln in body.split("\n")
            if ln.strip()
        ]
        if not lines:
            lines = [body[:120]] if body else []

        if hook:
            slides.append({
                "category": "الخطاف",
                "tool_name": "Hook",
                "headline": hook[:100],
                "detail": cues[:80] if cues else "",
            })
        for i, line in enumerate(lines[:6]):
            slides.append({
                "category": "النقطة " + str(i + 1),
                "tool_name": "Body",
                "headline": line[:100],
                "detail": "",
            })
        if cta:
            slides.append({
                "category": "الدعوة",
                "tool_name": "CTA",
                "headline": cta[:100],
                "detail": "",
            })

    elif content_type == "CAROUSEL":
        raw_slides = generated_content.get("slides", [])
        title = generated_content.get("title", "")
        if title:
            slides.append({
                "category": "المقدمة",
                "tool_name": "كاروسيل",
                "headline": title[:100],
                "detail": "",
            })
        for s in raw_slides:
            heading = s.get("heading", "")
            body    = s.get("body", "")
            tips    = s.get("tips_list") or []
            detail  = tips[0] if tips else body[:80]
            slides.append({
                "category": "نقطة",
                "tool_name": "كاروسيل",
                "headline": heading[:100],
                "detail": detail,
            })

    elif content_type == "POST":
        post = generated_content.get("unified_post", "")
        lines = [ln.strip() for ln in post.split("\n") if ln.strip()]
        for i, line in enumerate(lines[:5]):
            slides.append({
                "category": "البوست " + str(i + 1),
                "tool_name": "Post",
                "headline": line[:100],
                "detail": "",
            })

    if not slides:
        slides = [{"category": "محتوى", "tool_name": "", "headline": "لا يوجد محتوى", "detail": ""}]

    return slides
