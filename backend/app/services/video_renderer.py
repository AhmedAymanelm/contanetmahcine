"""
Video Renderer — Premium Slideshow MP4
Format: 1080x1920 (9:16 vertical — Reels/TikTok)
Features:
  - Single browser session (fast — no repeated browser launches)
  - Typing animation (text reveals character by character)
  - Animated segmented progress bar (fills during each slide)
  - Bar charts for numeric comparisons
  - Outro slide with article image + title
  - Article title in footer
"""

import asyncio
import base64
import math
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
from PIL import Image

OUTPUT_DIR = Path(__file__).parent.parent.parent / "static" / "video_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Easing ────────────────────────────────────────────────────────────────────
def _ease_in_out_cubic(t: float) -> float:
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2


# ── Segmented progress bar (RTL — fills right to left) ───────────────────────
def _progress_bar_html(current: int, total: int, fill: float) -> str:
    n = min(total, 12)
    parts = []
    for i in range(n):
        seg = i + 1
        if seg < current:
            # completed segment — fully filled
            inner = (
                '<div style="position:absolute;top:0;left:0;right:0;bottom:0;'
                'background:linear-gradient(270deg,#6366f1,#a855f7);border-radius:3px;"></div>'
            )
        elif seg == current:
            # active segment — fills from RIGHT to LEFT
            pct = round(fill * 100, 1)
            inner = (
                '<div style="position:absolute;top:0;right:0;bottom:0;'
                'width:' + str(pct) + '%;'
                'background:linear-gradient(270deg,#6366f1,#a855f7);border-radius:3px;'
                'box-shadow:0 0 10px rgba(99,102,241,0.8);"></div>'
            )
        else:
            inner = ""
        parts.append(
            '<div style="flex:1;height:6px;background:rgba(255,255,255,0.1);'
            'border-radius:3px;position:relative;overflow:hidden;">'
            + inner + "</div>"
        )
    # RTL: segment 1 on the right — use direction:rtl on the flex container
    return (
        '<div style="display:flex;gap:6px;align-items:center;flex:1;direction:rtl;">'
        + "".join(parts) + "</div>"
    )


# ── Bar chart ─────────────────────────────────────────────────────────────────
def _bar_chart_html(bars: List[Dict], opacity: float = 1.0) -> str:
    if not bars:
        return ""
    colors = ["#6366f1", "#a855f7", "#ec4899", "#f59e0b", "#10b981"]
    rows = ""
    for i, bar in enumerate(bars[:4]):
        label = bar.get("label", "")
        pct   = max(0, min(100, bar.get("pct", 0)))
        color = bar.get("color", colors[i % len(colors)])
        val   = bar.get("value", "")
        rows += (
            '<div style="display:flex;flex-direction:column;gap:6px;">'
            '<div style="display:flex;justify-content:space-between;">'
            '<span style="font-size:28px;font-weight:600;color:rgba(255,255,255,0.75);">' + label + "</span>"
            '<span style="font-size:30px;font-weight:900;color:' + color + ';">' + str(val) + "</span>"
            "</div>"
            '<div style="height:14px;background:rgba(255,255,255,0.07);border-radius:7px;overflow:hidden;">'
            '<div style="width:' + str(pct) + '%;height:100%;'
            'background:linear-gradient(90deg,' + color + ",rgba(255,255,255,0.5));"
            'border-radius:7px;box-shadow:0 0 8px ' + color + '66;"></div>'
            "</div></div>"
        )
    return (
        '<div style="width:100%;display:flex;flex-direction:column;gap:18px;opacity:'
        + str(round(opacity, 2)) + ';">' + rows + "</div>"
    )


# ── Slide HTML ────────────────────────────────────────────────────────────────
def _slide_html(
    slide: dict,
    cairo_css: str,
    reveal: float = 1.0,
    pfill: float = 1.0,
) -> str:
    number    = slide.get("number", "01")
    category  = slide.get("category", "")
    label     = slide.get("label", "")
    headline  = slide.get("headline", "")
    detail    = slide.get("detail", "")
    bars      = slide.get("bars", [])
    total     = slide.get("total", 1)
    current   = slide.get("current", 1)
    brand     = slide.get("brand", "غرفة المحتوى")
    article_title = slide.get("article_title", "")
    is_cover  = slide.get("is_cover", False)
    is_outro  = slide.get("is_outro", False)
    image_url = slide.get("image_url", "")

    prog_html = _progress_bar_html(current, total, pfill)
    counter   = str(current) + " / " + str(total)
    footer_label = article_title or brand

    # Full text = headline + detail merged (typing reveals both together)
    full_text = headline
    if detail:
        full_text = headline + (" — " if headline else "") + detail

    if reveal < 1.0:
        chars = max(1, int(len(full_text) * reveal))
        vis_full = full_text[:chars]
        cursor = '<span style="color:#6366f1;">|</span>'
    else:
        vis_full = full_text
        cursor = ""

    # Bars appear after 0.7
    bars_op = min(1.0, max(0.0, (reveal - 0.7) / 0.3)) if bars else 0.0

    # ── OUTRO ────────────────────────────────────────────────────────────────
    if is_outro:
        img_block = ""
        if image_url:
            img_block = (
                '<div style="width:100%;height:380px;border-radius:24px;overflow:hidden;'
                'box-shadow:0 20px 60px rgba(0,0,0,0.5);margin-bottom:28px;">'
                '<img src="' + image_url + '" style="width:100%;height:100%;object-fit:cover;"/>'
                "</div>"
            )
        card_body = (
            '<div style="display:flex;flex-direction:column;align-items:center;gap:22px;width:100%;">'
            + img_block
            + '<div style="font-size:32px;font-weight:700;color:rgba(255,255,255,0.4);">' + category + "</div>"
            + '<div style="font-size:72px;font-weight:900;color:#fff;text-align:center;line-height:1.3;">'
            + vis_full + cursor + "</div>"
            + '<div style="width:70px;height:4px;background:linear-gradient(270deg,#6366f1,#a855f7);border-radius:2px;"></div>'
            + "</div>"
        )
        card_html = '<div style="width:880px;padding:50px 56px;">' + card_body + "</div>"

    # ── COVER ────────────────────────────────────────────────────────────────
    elif is_cover:
        card_body = (
            '<div style="display:flex;flex-direction:column;align-items:center;gap:32px;width:100%;">'
            + '<div style="width:100px;height:4px;background:linear-gradient(270deg,#6366f1,#a855f7);border-radius:2px;"></div>'
            + '<div style="font-size:38px;font-weight:700;color:rgba(255,255,255,0.38);letter-spacing:3px;">' + (category or "") + "</div>"
            + '<div style="font-size:84px;font-weight:900;color:#fff;text-align:center;line-height:1.25;text-shadow:0 4px 30px rgba(0,0,0,0.5);">'
            + vis_full + cursor + "</div>"
            + "</div>"
        )
        card_html = '<div style="width:880px;padding:80px 56px;display:flex;flex-direction:column;align-items:center;">' + card_body + "</div>"

    # ── NORMAL ───────────────────────────────────────────────────────────────
    else:
        badge_row = ""
        if category or label:
            b = ""
            if category:
                b += (
                    '<div style="background:rgba(99,102,241,0.2);border:1px solid rgba(99,102,241,0.45);'
                    'color:#a5b4fc;padding:8px 24px;border-radius:40px;font-size:28px;font-weight:700;">'
                    + category + "</div>"
                )
            if label:
                b += (
                    '<div style="background:rgba(168,85,247,0.15);border:1px solid rgba(168,85,247,0.35);'
                    'color:#d8b4fe;padding:8px 24px;border-radius:40px;font-size:28px;font-weight:700;">'
                    + label + "</div>"
                )
            badge_row = '<div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:flex-end;">' + b + "</div>"

        bars_block = _bar_chart_html(bars, opacity=bars_op) if bars else ""

        card_body = (
            '<div style="display:flex;flex-direction:column;align-items:flex-end;gap:26px;width:100%;">'
            '<div style="display:flex;align-items:flex-start;justify-content:space-between;width:100%;">'
            '<div style="font-size:170px;font-weight:900;color:rgba(255,255,255,0.05);line-height:1;" dir="ltr">' + number + "</div>"
            '<div style="width:44px;height:4px;background:linear-gradient(270deg,#6366f1,#a855f7);border-radius:2px;margin-top:20px;"></div>'
            "</div>"
            + badge_row
            # Merged headline + detail as one flowing text block
            + '<div style="font-size:66px;font-weight:900;color:#fff;line-height:1.4;text-align:right;width:100%;margin-top:-14px;">'
            + vis_full + cursor + "</div>"
            + bars_block + "</div>"
        )
        card_html = (
            '<div style="width:880px;background:rgba(255,255,255,0.03);'
            'border:1px solid rgba(255,255,255,0.08);border-radius:36px;padding:56px 52px;'
            'box-shadow:0 24px 72px rgba(0,0,0,0.35);">'
            + card_body + "</div>"
        )

    body_bg = (
        "* { margin:0; padding:0; box-sizing:border-box; font-family:'Cairo',sans-serif; }"
        "html, body { width:1080px; height:1920px; overflow:hidden; }"
        "body { background:linear-gradient(145deg,#0a0a14 0%,#12102a 45%,#0a1018 100%);"
        "display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative; }"
        "body::before { content:'';position:absolute;top:-150px;right:-150px;width:650px;height:650px;"
        "background:radial-gradient(circle,rgba(99,102,241,0.16) 0%,transparent 70%);pointer-events:none; }"
        "body::after { content:'';position:absolute;bottom:-150px;left:-150px;width:650px;height:650px;"
        "background:radial-gradient(circle,rgba(168,85,247,0.12) 0%,transparent 70%);pointer-events:none; }"
    )

    return (
        "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>"
        + cairo_css + body_bg + "</style></head><body>"
        + '<div style="position:absolute;top:0;left:0;right:0;height:3px;'
        'background:linear-gradient(90deg,#6366f1,#a855f7,#ec4899);z-index:20;"></div>'
        + '<div style="position:absolute;top:60px;left:60px;right:60px;'
        'display:flex;align-items:center;gap:20px;z-index:10;">'
        + prog_html
        + '<span style="font-size:26px;color:rgba(255,255,255,0.3);font-weight:600;white-space:nowrap;">'
        + counter + "</span></div>"
        + '<div style="position:relative;z-index:5;display:flex;flex-direction:column;'
        'align-items:center;justify-content:center;width:100%;padding:160px 0;">'
        + card_html + "</div>"
        + '<div style="position:absolute;bottom:60px;left:60px;right:60px;'
        'display:flex;justify-content:space-between;align-items:center;'
        'border-top:1px solid rgba(255,255,255,0.06);padding-top:26px;z-index:10;">'
        + '<span style="font-size:26px;color:rgba(255,255,255,0.22);">احفظه</span>'
        + '<span style="font-size:26px;font-weight:700;color:rgba(255,255,255,0.48);'
        'max-width:700px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">'
        + footer_label + "</span></div>"
        + "</body></html>"
    )


# ── Slide transition ──────────────────────────────────────────────────────────
def _make_transition(img_a: Image.Image, img_b: Image.Image, n: int = 16) -> List[np.ndarray]:
    frames = []
    w, h = img_a.width, img_a.height
    for i in range(n):
        t = _ease_in_out_cubic(i / n)
        offset = int(w * t)
        combined = Image.new("RGB", (w, h))
        if offset < w:
            combined.paste(img_a.crop((offset, 0, w, h)), (0, 0))
        if offset > 0:
            combined.paste(img_b.crop((0, 0, offset, h)), (w - offset, 0))
        frames.append(np.array(combined))
    return frames


# ── Core: render all slides using ONE browser session ─────────────────────────
async def _render_all_slides(
    slides_data: List[Dict[str, Any]],
    cairo_css: str,
    fps: int = 30,
    type_sec: float = 0.8,
    hold_sec: float = 2.2,
) -> List[List[np.ndarray]]:
    """
    Opens browser once, renders all keyframes using the same page.
    Returns list of frame arrays per slide.
    """
    from playwright.async_api import async_playwright

    total_slides = len(slides_data)
    type_frames  = int(type_sec * fps)
    hold_frames  = int(hold_sec * fps)

    # Keyframe steps for typing phase
    TYPE_STEPS = 10  # how many distinct typing frames per slide
    HOLD_STEPS = 6   # how many distinct hold frames per slide (progress bar moves)

    all_slide_frames: List[List[np.ndarray]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page(viewport={"width": 1080, "height": 1920})

        for s_idx, slide in enumerate(slides_data):
            # Type keyframes: reveal 0→1, pfill 0→0.4
            type_cache: List[np.ndarray] = []
            for step in range(TYPE_STEPS + 1):
                reveal = step / TYPE_STEPS
                pfill  = reveal * 0.4
                html   = _slide_html(slide, cairo_css, reveal=reveal, pfill=pfill)
                await page.set_content(html, wait_until="domcontentloaded")
                png_bytes = await page.screenshot(full_page=False)
                from io import BytesIO
                arr = np.array(Image.open(BytesIO(png_bytes)).convert("RGB"))
                type_cache.append(arr)

            # Hold keyframes: reveal=1, pfill 0.4→1.0
            hold_cache: List[np.ndarray] = []
            for step in range(HOLD_STEPS + 1):
                pfill = 0.4 + 0.6 * (step / HOLD_STEPS)
                html  = _slide_html(slide, cairo_css, reveal=1.0, pfill=pfill)
                await page.set_content(html, wait_until="domcontentloaded")
                png_bytes = await page.screenshot(full_page=False)
                arr = np.array(Image.open(BytesIO(png_bytes)).convert("RGB"))
                hold_cache.append(arr)

            # Build frame list for this slide
            slide_frames: List[np.ndarray] = []

            # Typing phase
            for f in range(type_frames):
                idx = min(int(f / type_frames * TYPE_STEPS), TYPE_STEPS)
                slide_frames.append(type_cache[idx])

            # Hold phase
            for f in range(hold_frames):
                idx = min(int(f / hold_frames * HOLD_STEPS), HOLD_STEPS)
                slide_frames.append(hold_cache[idx])

            all_slide_frames.append(slide_frames)

        await browser.close()

    return all_slide_frames


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
    for idx, slide in enumerate(slides_data):
        slide["number"]  = str(idx + 1).zfill(2)
        slide["total"]   = total
        slide["current"] = idx + 1

    # Render all slides frames (single browser session)
    all_slide_frames = await _render_all_slides(
        slides_data, CAIRO_FONT_CSS, fps=fps, type_sec=0.8, hold_sec=2.2
    )

    # Assemble with transitions
    all_frames: List[np.ndarray] = []
    prev_img: Optional[Image.Image] = None

    for s_frames in all_slide_frames:
        if prev_img is not None and s_frames:
            next_img   = Image.fromarray(s_frames[0])
            transition = _make_transition(prev_img, next_img, n=16)
            all_frames.extend(transition)
        all_frames.extend(s_frames)
        if s_frames:
            prev_img = Image.fromarray(s_frames[-1])

    # Write MP4
    timestamp    = int(time.time())
    out_filename = "video_" + str(content_item_id) + "_" + str(timestamp) + ".mp4"
    out_path     = OUTPUT_DIR / out_filename
    duration     = len(all_frames) / fps

    def make_frame(t):
        return all_frames[min(int(t * fps), len(all_frames) - 1)]

    clip = VideoClip(make_frame, duration=duration)
    clip.write_videofile(
        str(out_path), fps=fps, codec="libx264", audio=False,
        preset="fast", ffmpeg_params=["-crf", "20", "-pix_fmt", "yuv420p"],
        logger=None,
    )

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


# ── Extract bars ──────────────────────────────────────────────────────────────
def _extract_bars_from_text(text: str) -> List[Dict]:
    import re
    bars   = []
    colors = ["#6366f1", "#a855f7", "#ec4899", "#f59e0b", "#10b981"]
    pats   = re.findall(r'([^\n،,]+?)[\s:]+(\d+(?:\.\d+)?)\s*(%|من|\/\d+)?', text)
    for i, m in enumerate(pats[:4]):
        try:
            num = float(m[1])
            unit = m[2] or ""
            pct = min(num, 100) if "%" in unit else min(num * 10, 100)
            disp = m[1] + ("%" if "%" in unit else "")
            bars.append({"label": m[0].strip()[:30], "pct": round(pct), "value": disp,
                         "color": colors[i % len(colors)]})
        except (ValueError, IndexError):
            continue
    return bars


# ── Content → slides ──────────────────────────────────────────────────────────
def content_item_to_slides(
    generated_content: dict,
    content_type: str,
    brand: str = "غرفة المحتوى",
    article_title: str = "",
    image_url: str = "",
) -> List[Dict[str, Any]]:
    slides: List[Dict[str, Any]] = []

    def base(extra: dict) -> dict:
        return {"brand": brand, "article_title": article_title, "bars": [], **extra}

    if content_type == "VIDEO_SCRIPT":
        hook  = generated_content.get("hook", "")
        body  = generated_content.get("body", "")
        cta   = generated_content.get("call_to_action", "")
        cues  = generated_content.get("visual_cues", "")
        lines = [ln.strip().lstrip("-•* ").strip() for ln in body.split("\n") if ln.strip()]
        if not lines:
            lines = [body[:120]] if body else []
        if hook:
            slides.append(base({"is_cover": True, "category": "ابدأ من هنا",
                                 "label": "", "headline": hook[:130],
                                 "detail": cues[:100] if cues else ""}))
        for i, line in enumerate(lines[:6]):
            slides.append(base({"category": "نقطة", "label": str(i + 1),
                                 "headline": line[:110], "detail": "",
                                 "bars": _extract_bars_from_text(line)}))
        if cta:
            slides.append(base({"category": "الآن", "label": "",
                                 "headline": cta[:110], "detail": ""}))

    elif content_type == "CAROUSEL":
        raw_slides = generated_content.get("slides", [])
        title      = generated_content.get("title", "")
        if title:
            slides.append(base({"is_cover": True, "category": "اكتشف",
                                 "label": "", "headline": title[:130], "detail": ""}))
        for i, s in enumerate(raw_slides):
            heading = s.get("heading", "")
            body    = s.get("body", "")
            tips    = s.get("tips_list") or []
            detail  = tips[0] if tips else body[:100]
            slides.append(base({"category": "نقطة", "label": str(i + 1),
                                 "headline": heading[:110], "detail": detail,
                                 "bars": _extract_bars_from_text(body) if body else []}))

    elif content_type == "POST":
        post  = generated_content.get("unified_post", "")
        lines = [ln.strip() for ln in post.split("\n") if ln.strip()]
        for i, line in enumerate(lines[:6]):
            slides.append(base({"category": "بوست", "label": str(i + 1),
                                 "headline": line[:110], "detail": ""}))

    if not slides:
        slides = [base({"category": "محتوى", "label": "", "headline": "لا يوجد محتوى", "detail": ""})]

    # Outro slide (article image + title)
    if article_title:
        slides.append(base({
            "is_outro": True,
            "category": "اقرأ المقال كاملاً",
            "label": "",
            "headline": article_title[:120],
            "detail": brand,
            "image_url": image_url,
        }))

    return slides
