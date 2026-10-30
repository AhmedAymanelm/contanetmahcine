"""
Video Renderer — Premium Slideshow MP4 with Typing Animation + Bar Charts
Format: 1080×1920 (9:16 vertical — Reels/TikTok)
Style: Dark premium gradient, big bold text, typing effect, comparison bars
"""

import asyncio
import os
import time
import math
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).parent.parent.parent / "static" / "video_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SLIDE_ICONS = ["🔥", "💡", "⚡", "🎯", "🚀", "📊", "🌟", "🔑", "✨", "📌"]

# ── Easing functions ─────────────────────────────────────────────────────────
def _ease_out_expo(t: float) -> float:
    return 1.0 if t >= 1.0 else 1.0 - math.pow(2.0, -10.0 * t)

def _ease_in_out_cubic(t: float) -> float:
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2


# ── HTML builder for each slide ───────────────────────────────────────────────
def _bar_chart_html(bars: List[Dict]) -> str:
    """Generate animated-looking bar chart HTML for comparison slides."""
    if not bars:
        return ""
    html = '<div style="width:100%;display:flex;flex-direction:column;gap:22px;margin-top:10px;">'
    for bar in bars:
        label = bar.get("label", "")
        pct   = max(0, min(100, bar.get("pct", 0)))
        color = bar.get("color", "#6366f1")
        val   = bar.get("value", "")
        html += (
            '<div style="display:flex;flex-direction:column;gap:8px;">'
            '<div style="display:flex;justify-content:space-between;align-items:center;">'
            '<span style="font-size:32px;font-weight:700;color:rgba(255,255,255,0.85);">' + label + '</span>'
            '<span style="font-size:34px;font-weight:900;color:' + color + ';">' + str(val) + '</span>'
            '</div>'
            '<div style="width:100%;height:18px;background:rgba(255,255,255,0.08);border-radius:9px;overflow:hidden;">'
            '<div style="width:' + str(pct) + '%;height:100%;background:linear-gradient(90deg,' + color + ',rgba(255,255,255,0.6));'
            'border-radius:9px;box-shadow:0 0 12px ' + color + '88;"></div>'
            '</div>'
            '</div>'
        )
    html += '</div>'
    return html


def _progress_dots_html(current: int, total: int) -> str:
    parts = []
    for i in range(min(total, 10)):
        is_active = (i + 1 == current)
        if is_active:
            parts.append('<div style="width:32px;height:6px;border-radius:3px;background:#6366f1;box-shadow:0 0 8px #6366f188;"></div>')
        else:
            parts.append('<div style="width:6px;height:6px;border-radius:3px;background:rgba(255,255,255,0.2);"></div>')
    return "".join(parts)


def _slide_html(slide: dict, cairo_css: str, reveal_ratio: float = 1.0) -> str:
    """
    Build full HTML for a slide.
    reveal_ratio 0.0 = no text shown, 1.0 = fully revealed (for typing frames).
    """
    number   = slide.get("number", "01")
    icon     = slide.get("icon", "📌")
    category = slide.get("category", "")
    label    = slide.get("label", "")
    headline = slide.get("headline", "")
    detail   = slide.get("detail", "")
    bars     = slide.get("bars", [])  # list of {label, pct, value, color}
    total    = slide.get("total", 1)
    current  = slide.get("current", 1)
    brand    = slide.get("brand", "غرفة المحتوى")
    is_cover = slide.get("is_cover", False)

    dots_html = _progress_dots_html(current, total)

    # Apply typing reveal to headline
    if reveal_ratio < 1.0:
        chars_to_show = max(1, int(len(headline) * reveal_ratio))
        visible_headline = headline[:chars_to_show]
        cursor = '<span style="opacity:0.9;animation:none;">|</span>'
    else:
        visible_headline = headline
        cursor = ""

    # Detail reveal (starts after headline is done)
    detail_reveal = max(0.0, (reveal_ratio - 0.7) / 0.3) if detail else 0.0
    if detail_reveal < 1.0 and detail:
        chars_d = max(0, int(len(detail) * detail_reveal))
        visible_detail = detail[:chars_d]
    else:
        visible_detail = detail

    # Bars reveal (shows only when reveal_ratio > 0.6)
    bars_opacity = min(1.0, max(0.0, (reveal_ratio - 0.6) / 0.4)) if bars else 0.0

    bar_html = ""
    if bars and bars_opacity > 0:
        bar_html = (
            '<div style="opacity:' + str(round(bars_opacity, 2)) + ';width:100%;">'
            + _bar_chart_html(bars)
            + '</div>'
        )

    # Cover slide layout vs normal
    if is_cover:
        detail_part = ""
        if visible_detail:
            detail_part = (
                '<div style="font-size:42px;font-weight:500;color:rgba(255,255,255,0.6);text-align:center;line-height:1.5;">'
                + visible_detail + "</div>"
            )
        card_inner = (
            '<div style="display:flex;flex-direction:column;align-items:center;gap:36px;width:100%;">'
            '<div style="width:180px;height:180px;background:linear-gradient(135deg,#6366f1,#a855f7);'
            'border-radius:40px;display:flex;align-items:center;justify-content:center;font-size:90px;'
            'box-shadow:0 20px 60px rgba(99,102,241,0.5);">' + icon + "</div>"
            '<div style="font-size:44px;font-weight:700;color:rgba(255,255,255,0.5);letter-spacing:4px;">'
            + (category or "") + "</div>"
            '<div style="font-size:90px;font-weight:900;color:#fff;line-height:1.2;text-align:center;'
            'text-shadow:0 4px 30px rgba(0,0,0,0.5);">'
            + visible_headline + cursor + "</div>"
            + detail_part
            + "</div>"
        )
    else:
        cat_badge_html = ""
        if category:
            cat_badge_html = (
                '<div style="background:rgba(99,102,241,0.25);border:1px solid rgba(99,102,241,0.5);'
                'color:#a5b4fc;padding:10px 26px;border-radius:50px;font-size:30px;font-weight:700;">'
                + category + "</div>"
            )
        lbl_badge_html = ""
        if label:
            lbl_badge_html = (
                '<div style="background:rgba(168,85,247,0.2);border:1px solid rgba(168,85,247,0.4);'
                'color:#d8b4fe;padding:10px 26px;border-radius:50px;font-size:30px;font-weight:700;">'
                + label + "</div>"
            )
        badges_row = ""
        if category or label:
            badges_row = (
                '<div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:flex-end;">'
                + cat_badge_html + lbl_badge_html + "</div>"
            )
        detail_box = ""
        if visible_detail:
            detail_box = (
                '<div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);'
                'border-radius:20px;padding:28px 32px;width:100%;text-align:right;">'
                '<span style="font-size:36px;color:rgba(255,255,255,0.65);line-height:1.6;">'
                + visible_detail + "</span></div>"
            )
        card_inner = (
            '<div style="display:flex;flex-direction:column;align-items:flex-end;gap:30px;width:100%;">'
            '<div style="display:flex;align-items:center;justify-content:space-between;width:100%;">'
            '<div style="font-size:160px;font-weight:900;color:rgba(255,255,255,0.08);line-height:1;" dir="ltr">'
            + number + "</div>"
            '<div style="width:110px;height:110px;background:linear-gradient(135deg,#6366f1,#a855f7);'
            'border-radius:28px;display:flex;align-items:center;justify-content:center;font-size:54px;'
            'box-shadow:0 8px 32px rgba(99,102,241,0.5);">' + icon + "</div>"
            "</div>"
            + badges_row
            + '<div style="font-size:74px;font-weight:900;color:#fff;line-height:1.3;text-align:right;width:100%;'
            'text-shadow:0 4px 20px rgba(0,0,0,0.4);">'
            + visible_headline + cursor + "</div>"
            + detail_box
            + bar_html
            + "</div>"
        )

    return """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
""" + cairo_css + """
* { margin:0; padding:0; box-sizing:border-box; font-family:'Cairo',sans-serif; }
html, body { width:1080px; height:1920px; overflow:hidden; }
body {
    background: linear-gradient(145deg, #0f0f1a 0%, #1a1030 40%, #0d1520 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
}
/* Decorative glow blobs */
body::before {
    content:'';position:absolute;top:-200px;right:-200px;
    width:700px;height:700px;
    background:radial-gradient(circle,rgba(99,102,241,0.18) 0%,transparent 70%);
    pointer-events:none;
}
body::after {
    content:'';position:absolute;bottom:-200px;left:-200px;
    width:700px;height:700px;
    background:radial-gradient(circle,rgba(168,85,247,0.14) 0%,transparent 70%);
    pointer-events:none;
}
</style>
</head>
<body>

  <!-- Top bar: progress dots + counter -->
  <div style="position:absolute;top:80px;right:60px;left:60px;
              display:flex;justify-content:space-between;align-items:center;z-index:10;">
    <div style="display:flex;gap:10px;align-items:center;">""" + dots_html + """</div>
    <span style="font-size:30px;color:rgba(255,255,255,0.35);font-weight:600;">
      """ + str(current) + """ / """ + str(total) + """
    </span>
  </div>

  <!-- Decorative top accent line -->
  <div style="position:absolute;top:0;left:0;right:0;height:4px;
              background:linear-gradient(90deg,#6366f1,#a855f7,#ec4899);"></div>

  <!-- Main card -->
  <div style="width:900px;
              background:rgba(255,255,255,0.04);
              border:1px solid rgba(255,255,255,0.1);
              border-radius:40px;
              padding:70px 60px;
              box-shadow:0 30px 80px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1);
              backdrop-filter:blur(20px);
              position:relative;z-index:5;">
    """ + card_inner + """
  </div>

  <!-- Footer -->
  <div style="position:absolute;bottom:70px;right:60px;left:60px;
              display:flex;justify-content:space-between;align-items:center;
              border-top:1px solid rgba(255,255,255,0.07);padding-top:30px;z-index:10;">
    <span style="font-size:28px;color:rgba(255,255,255,0.3);font-weight:600;">احفظه 🔖</span>
    <span style="font-size:28px;font-weight:800;
                 background:linear-gradient(90deg,#6366f1,#a855f7);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
      """ + brand + """
    </span>
  </div>

</body>
</html>"""


# ── Playwright render ─────────────────────────────────────────────────────────
async def _render_slide_png(html: str, output_path: Path):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(path=str(output_path), full_page=False)
        await browser.close()


# ── Slide-in transition (horizontal) ─────────────────────────────────────────
def _make_slide_transition(
    img_a: Image.Image, img_b: Image.Image, n_frames: int = 20
) -> List[np.ndarray]:
    frames = []
    w, h = img_a.width, img_a.height
    for i in range(n_frames):
        t = _ease_in_out_cubic(i / n_frames)
        offset = int(w * t)
        combined = Image.new("RGB", (w, h))
        if offset < w:
            combined.paste(img_a.crop((offset, 0, w, h)), (0, 0))
        if offset > 0:
            combined.paste(img_b.crop((0, 0, offset, h)), (w - offset, 0))
        frames.append(np.array(combined))
    return frames


# ── Build typing frames for a single slide ───────────────────────────────────
async def _render_typing_frames(
    slide: dict,
    cairo_css: str,
    tmp_dir: Path,
    slide_idx: int,
    fps: int = 30,
    hold_sec: float = 2.5,
    type_sec: float = 1.0,
) -> List[np.ndarray]:
    """
    Renders multiple frames with progressive text reveal (typing effect).
    Returns list of numpy arrays.
    """
    total_frames = int((type_sec + hold_sec) * fps)
    type_frames  = int(type_sec * fps)
    hold_frames  = total_frames - type_frames

    headline = slide.get("headline", "")
    has_detail = bool(slide.get("detail", "") or slide.get("bars", []))

    frames_out: List[np.ndarray] = []
    rendered_cache: Dict[float, np.ndarray] = {}

    # Determine keyframe ratios to render (avoid rendering every frame)
    key_ratios = []
    steps = max(12, len(headline) // 4)
    for s in range(steps + 1):
        ratio = s / steps
        key_ratios.append(round(ratio, 3))
    key_ratios.append(1.0)
    key_ratios = sorted(set(key_ratios))

    # Render keyframes
    for ratio in key_ratios:
        png_path = tmp_dir / ("typing_" + str(slide_idx) + "_" + str(int(ratio * 1000)).zfill(4) + ".png")
        html = _slide_html(slide, cairo_css, reveal_ratio=ratio)
        await _render_slide_png(html, png_path)
        img = np.array(Image.open(str(png_path)).convert("RGB"))
        rendered_cache[ratio] = img
        try:
            png_path.unlink()
        except Exception:
            pass

    # Build frame sequence — typing phase
    for f in range(type_frames):
        ratio = f / max(type_frames - 1, 1)
        # Find nearest cached ratio
        nearest = min(key_ratios, key=lambda r: abs(r - ratio))
        frames_out.append(rendered_cache[nearest])

    # Hold phase — fully revealed
    frames_out.extend([rendered_cache[1.0]] * hold_frames)

    return frames_out


# ── Main async render ─────────────────────────────────────────────────────────
async def render_video(
    slides_data: List[Dict[str, Any]],
    content_item_id: int,
    brand: str = "غرفة المحتوى",
    fps: int = 30,
) -> str:
    from moviepy.editor import VideoClip

    try:
        from app.services.cairo_font_embedded import CAIRO_FONT_CSS
    except ImportError:
        CAIRO_FONT_CSS = ""

    total = len(slides_data)
    timestamp = int(time.time())
    tmp_dir = OUTPUT_DIR / ("tmp_" + str(content_item_id) + "_" + str(timestamp))
    tmp_dir.mkdir(parents=True, exist_ok=True)

    all_frames: List[np.ndarray] = []
    prev_img: Optional[Image.Image] = None

    for idx, slide in enumerate(slides_data):
        slide["number"] = str(idx + 1).zfill(2)
        if not slide.get("icon"):
            slide["icon"] = SLIDE_ICONS[idx % len(SLIDE_ICONS)]
        slide["total"] = total
        slide["current"] = idx + 1
        slide["brand"] = brand

        # Render typing frames for this slide
        slide_frames = await _render_typing_frames(
            slide, CAIRO_FONT_CSS, tmp_dir, idx,
            fps=fps,
            hold_sec=2.5,
            type_sec=1.0,
        )

        # Add transition from previous slide
        if prev_img is not None and slide_frames:
            first_frame_img = Image.fromarray(slide_frames[0])
            transition = _make_slide_transition(prev_img, first_frame_img, n_frames=20)
            all_frames.extend(transition)

        all_frames.extend(slide_frames)

        # Save last frame as PIL Image for next transition
        if slide_frames:
            prev_img = Image.fromarray(slide_frames[-1])

    # Write MP4
    out_filename = "video_" + str(content_item_id) + "_" + str(timestamp) + ".mp4"
    out_path = OUTPUT_DIR / out_filename

    total_duration = len(all_frames) / fps

    def make_frame(t):
        frame_idx = min(int(t * fps), len(all_frames) - 1)
        return all_frames[frame_idx]

    clip = VideoClip(make_frame, duration=total_duration)
    clip.write_videofile(
        str(out_path),
        fps=fps,
        codec="libx264",
        audio=False,
        preset="fast",
        ffmpeg_params=["-crf", "20", "-pix_fmt", "yuv420p"],
        logger=None,
    )

    # Cleanup
    try:
        for f in tmp_dir.iterdir():
            f.unlink()
        tmp_dir.rmdir()
    except Exception:
        pass

    return "/static/video_output/" + out_filename


def render_video_sync(
    slides_data: List[Dict[str, Any]],
    content_item_id: int,
    brand: str = "غرفة المحتوى",
    fps: int = 30,
) -> str:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            render_video(slides_data, content_item_id, brand, fps)
        )
    finally:
        loop.close()


# ── Content item → slides converter ──────────────────────────────────────────
def _extract_bars_from_text(text: str) -> List[Dict]:
    """Try to extract comparison data (numbers) from text to make bar chart."""
    import re
    bars = []
    colors = ["#6366f1", "#a855f7", "#ec4899", "#f59e0b", "#10b981", "#3b82f6"]
    # Look for patterns like "X%", "X من Y", "X/Y"
    pattern = re.findall(r'([^\n،,]+?)[\s:]+(\d+(?:\.\d+)?)\s*(%|من|\/\d+)?', text)
    for i, match in enumerate(pattern[:5]):
        label_raw = match[0].strip()[:30]
        val = float(match[2] if match[2] and match[2] != '%' and '/' not in match[2] else match[1])
        unit = match[2] or ""
        if "%" in unit:
            pct = min(float(match[1]), 100)
        else:
            pct = min(float(match[1]) * 10, 100)  # rough scale
        bars.append({
            "label": label_raw,
            "pct": round(pct),
            "value": match[1] + (unit if unit == "%" else ""),
            "color": colors[i % len(colors)],
        })
    return bars


def content_item_to_slides(
    generated_content: dict, content_type: str
) -> List[Dict[str, Any]]:
    slides: List[Dict[str, Any]] = []

    if content_type == "VIDEO_SCRIPT":
        hook = generated_content.get("hook", "")
        body = generated_content.get("body", "")
        cta  = generated_content.get("call_to_action", "")
        cues = generated_content.get("visual_cues", "")

        lines = [
            ln.strip().lstrip("-•* ").strip()
            for ln in body.split("\n")
            if ln.strip()
        ]
        if not lines:
            lines = [body[:120]] if body else []

        if hook:
            slides.append({
                "is_cover": True,
                "category": "ابدأ من هنا",
                "label": "",
                "headline": hook[:120],
                "detail": cues[:100] if cues else "",
                "icon": "🎬",
            })
        for i, line in enumerate(lines[:6]):
            bars = _extract_bars_from_text(line)
            slides.append({
                "category": "نقطة",
                "label": str(i + 1),
                "headline": line[:100],
                "detail": "",
                "bars": bars,
            })
        if cta:
            slides.append({
                "category": "CTA",
                "label": "",
                "headline": cta[:100],
                "detail": "",
                "icon": "👊",
            })

    elif content_type == "CAROUSEL":
        raw_slides = generated_content.get("slides", [])
        title = generated_content.get("title", "")

        if title:
            slides.append({
                "is_cover": True,
                "category": "اكتشف",
                "label": "",
                "headline": title[:120],
                "detail": "",
                "icon": "🚀",
            })

        for i, s in enumerate(raw_slides):
            heading = s.get("heading", "")
            body    = s.get("body", "")
            tips    = s.get("tips_list") or []
            detail  = tips[0] if tips else body[:100]
            bars    = _extract_bars_from_text(body) if body else []
            slides.append({
                "category": "نقطة",
                "label": str(i + 1),
                "headline": heading[:100],
                "detail": detail,
                "bars": bars,
            })

    elif content_type == "POST":
        post  = generated_content.get("unified_post", "")
        lines = [ln.strip() for ln in post.split("\n") if ln.strip()]
        for i, line in enumerate(lines[:6]):
            slides.append({
                "category": "بوست",
                "label": str(i + 1),
                "headline": line[:100],
                "detail": "",
                "bars": [],
            })

    if not slides:
        slides = [{
            "category": "محتوى",
            "label": "",
            "headline": "لا يوجد محتوى",
            "detail": "",
            "bars": [],
        }]

    return slides
