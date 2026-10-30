"""
Video Renderer — PREMIUM EDITORIAL
Format: 1080x1920 (9:16 — Reels/TikTok)

Design Philosophy:
  - ZERO boxes or cards — text directly on cinematic dark background
  - Ghost number (500px) bleeds off the right edge as graphic element
  - Orange accent line as the ONLY decorative element
  - Cinematic slide-up entrance (translateY + opacity per frame)
  - Word-by-word reveal for dramatic effect
  - Single thin progress bar at top (minimal, not segmented)
  - Bold editorial typography — no emojis, no clutter
"""

import asyncio
import math
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
from PIL import Image

OUTPUT_DIR = Path(__file__).parent.parent.parent / "static" / "video_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ACCENT   = "#FF5C00"   # deep orange
ACCENT2  = "#FFB700"   # amber (for covers)
BG       = "#080808"


# ── Easing ────────────────────────────────────────────────────────────────────
def _ease_out_expo(t: float) -> float:
    return 1.0 if t >= 1.0 else 1.0 - math.pow(2.0, -10.0 * t)

def _ease_in_out_cubic(t: float) -> float:
    return 4*t*t*t if t < 0.5 else 1 - math.pow(-2*t+2, 3)/2


# ── Top single-bar progress (RTL, fills right→left) ──────────────────────────
def _top_bar_html(current: int, total: int, pfill: float) -> str:
    """
    Single thin progress bar at very top.
    current: 1-based active slide
    pfill:   0-1 fill of current segment
    Total progress = ((current-1) + pfill) / total  →  overall % done
    """
    overall_pct = round(((current - 1 + pfill) / max(total, 1)) * 100, 2)
    return (
        '<div style="position:absolute;top:0;left:0;right:0;height:4px;'
        'background:rgba(255,255,255,0.07);z-index:100;">'
        '<div style="position:absolute;top:0;right:0;bottom:0;'
        'width:' + str(overall_pct) + '%;'
        'background:linear-gradient(270deg,' + ACCENT + ',' + ACCENT2 + ');'
        'box-shadow:0 0 16px ' + ACCENT + 'aa;"></div>'
        '</div>'
    )


# ── Bar chart ─────────────────────────────────────────────────────────────────
def _bar_chart_html(bars: List[Dict], opacity: float = 1.0) -> str:
    if not bars:
        return ""
    colors = [ACCENT, ACCENT2, "#00C9FF", "#a855f7", "#10b981"]
    rows = ""
    for i, bar in enumerate(bars[:4]):
        label = bar.get("label", "")
        pct   = max(0, min(100, bar.get("pct", 0)))
        color = bar.get("color", colors[i % len(colors)])
        val   = bar.get("value", "")
        rows += (
            '<div style="display:flex;flex-direction:column;gap:8px;">'
            '<div style="display:flex;justify-content:space-between;align-items:baseline;">'
            '<span style="font-size:32px;font-weight:700;color:rgba(255,255,255,0.7);">' + label + "</span>"
            '<span style="font-size:36px;font-weight:900;color:' + color + ';letter-spacing:-1px;">' + str(val) + "</span>"
            "</div>"
            '<div style="height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;">'
            '<div style="width:' + str(pct) + '%;height:100%;'
            'background:linear-gradient(270deg,' + color + ",rgba(255,255,255,0.3));"
            'border-radius:3px;box-shadow:0 0 10px ' + color + '88;"></div>'
            "</div></div>"
        )
    return (
        '<div style="display:flex;flex-direction:column;gap:20px;'
        'opacity:' + str(round(opacity, 2)) + ';">' + rows + "</div>"
    )


# ── Slide HTML ────────────────────────────────────────────────────────────────
def _slide_html(slide: dict, cairo_css: str, reveal: float = 1.0, pfill: float = 1.0) -> str:
    """
    reveal: 0-0.5 = entrance (slide-up), 0.5-1 = hold
    pfill:  progress bar fill 0-1
    """
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

    footer_label = article_title or brand
    top_bar = _top_bar_html(current, total, pfill)
    counter_str = str(current) + " / " + str(total)

    # Entrance animation: reveal 0→0.5 = slide up + fade in
    ent_t    = min(1.0, reveal / 0.5)
    ent_ease = _ease_out_expo(ent_t)
    h_y   = int(70 * (1.0 - ent_ease))   # headline translateY 70→0
    h_op  = round(ent_ease, 3)            # opacity 0→1

    # Detail appears slightly after headline (reveal 0.25→0.75)
    d_t    = min(1.0, max(0.0, (reveal - 0.2) / 0.4))
    d_ease = _ease_out_expo(d_t)
    d_y    = int(50 * (1.0 - d_ease))
    d_op   = round(d_ease, 3)

    # Bars after detail
    bars_t  = min(1.0, max(0.0, (reveal - 0.35) / 0.35))
    bars_op = _ease_out_expo(bars_t)

    # Full merged text for normal slides
    full_text = headline
    if detail:
        full_text = headline + (" — " if headline else "") + detail

    # Word-by-word reveal (split on spaces, reveal from right for RTL)
    def _reveal_words(text: str, ratio: float) -> str:
        words = text.split()
        if not words:
            return ""
        n = max(1, math.ceil(len(words) * ratio))
        return " ".join(words[:n])

    # During entrance phase, reveal words progressively
    if reveal < 0.5:
        vis_text = _reveal_words(full_text, ent_ease)
        cursor = ""
    else:
        vis_text = full_text
        cursor = ""

    css_base = (
        "* { margin:0; padding:0; box-sizing:border-box; font-family:'Cairo',sans-serif; }"
        "html, body { width:1080px; height:1920px; overflow:hidden; }"
        "body { background:" + BG + "; position:relative; overflow:hidden; }"
    )

    # ── OUTRO ────────────────────────────────────────────────────────────────
    if is_outro:
        overlay = ""
        if image_url:
            overlay = (
                '<div style="position:absolute;top:0;left:0;right:0;height:1080px;">'
                '<img src="' + image_url + '" style="width:100%;height:100%;object-fit:cover;"/>'
                '<div style="position:absolute;top:0;left:0;right:0;bottom:0;'
                'background:linear-gradient(to bottom,rgba(8,8,8,0.3) 0%,rgba(8,8,8,0.95) 70%,rgba(8,8,8,1) 100%);"></div>'
                '</div>'
            )
        content = (
            '<div style="position:absolute;bottom:280px;left:80px;right:80px;'
            'transform:translateY(' + str(h_y) + 'px);opacity:' + str(h_op) + ';">'
            '<div style="font-size:26px;font-weight:700;color:' + ACCENT + ';letter-spacing:4px;text-transform:uppercase;margin-bottom:28px;">'
            + (category or "اقرأ المزيد") + '</div>'
            '<div style="font-size:82px;font-weight:900;color:#fff;line-height:1.15;text-align:right;'
            'letter-spacing:-1px;text-shadow:0 4px 40px rgba(0,0,0,0.8);">'
            + vis_text + '</div>'
            '<div style="width:80px;height:4px;background:linear-gradient(270deg,' + ACCENT + ',' + ACCENT2 + ');margin-top:32px;margin-right:0;float:right;clear:both;"></div>'
            '</div>'
        )
        return (
            "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>"
            + cairo_css + css_base + "</style></head><body>"
            + top_bar + overlay + content
            + '<div style="position:absolute;bottom:80px;left:80px;right:80px;'
            'display:flex;justify-content:space-between;align-items:center;'
            'border-top:1px solid rgba(255,255,255,0.1);padding-top:28px;">'
            '<span style="font-size:24px;color:rgba(255,255,255,0.3);">احفظه</span>'
            '<span style="font-size:24px;color:rgba(255,255,255,0.4);">' + counter_str + '</span>'
            '</div>'
            "</body></html>"
        )

    # ── COVER ────────────────────────────────────────────────────────────────
    elif is_cover:
        # Big diagonal background strip
        deco = (
            '<div style="position:absolute;top:-200px;right:-200px;'
            'width:700px;height:700px;border-radius:50%;'
            'background:radial-gradient(circle,' + ACCENT + '18 0%,transparent 70%);pointer-events:none;"></div>'
            '<div style="position:absolute;bottom:-200px;left:-200px;'
            'width:600px;height:600px;border-radius:50%;'
            'background:radial-gradient(circle,' + ACCENT2 + '12 0%,transparent 70%);pointer-events:none;"></div>'
        )
        content = (
            '<div style="position:absolute;top:50%;left:80px;right:80px;'
            'transform:translateY(calc(-50% + ' + str(h_y) + 'px));opacity:' + str(h_op) + ';">'
            '<div style="font-size:30px;font-weight:700;color:' + ACCENT + ';letter-spacing:5px;'
            'text-transform:uppercase;margin-bottom:32px;text-align:center;">'
            + (category or "") + '</div>'
            '<div style="width:60px;height:4px;background:linear-gradient(270deg,' + ACCENT + ',' + ACCENT2 + ');margin:0 auto 40px;"></div>'
            '<div style="font-size:100px;font-weight:900;color:#fff;line-height:1.1;text-align:center;'
            'letter-spacing:-2px;text-shadow:0 8px 60px rgba(0,0,0,0.5);">'
            + vis_text + '</div>'
            '</div>'
        )
        return (
            "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>"
            + cairo_css + css_base + "</style></head><body>"
            + top_bar + deco + content
            + '<div style="position:absolute;bottom:80px;left:80px;right:80px;'
            'display:flex;justify-content:space-between;align-items:center;">'
            '<span style="font-size:24px;color:rgba(255,255,255,0.25);letter-spacing:2px;">' + footer_label + '</span>'
            '<span style="font-size:24px;color:rgba(255,255,255,0.25);">' + counter_str + '</span>'
            '</div>'
            "</body></html>"
        )

    # ── NORMAL SLIDE ─────────────────────────────────────────────────────────
    # Giant ghost number — bleeds off right edge, purely decorative
    ghost_num = (
        '<div style="position:absolute;right:-60px;top:50%;transform:translateY(-55%);'
        'font-size:520px;font-weight:900;color:rgba(255,255,255,0.03);'
        'line-height:1;pointer-events:none;user-select:none;" dir="ltr">'
        + number + '</div>'
    )

    # Category + label badges (top left, small + uppercase)
    badge_line = ""
    parts = []
    if category:
        parts.append(
            '<span style="color:' + ACCENT + ';font-size:26px;font-weight:700;letter-spacing:3px;text-transform:uppercase;">'
            + category + '</span>'
        )
    if label:
        parts.append(
            '<span style="color:rgba(255,255,255,0.4);font-size:26px;font-weight:600;letter-spacing:2px;">'
            + label + '</span>'
        )
    if parts:
        badge_line = (
            '<div style="display:flex;gap:20px;align-items:center;margin-bottom:32px;">'
            + '<div style="width:3px;height:28px;background:' + ACCENT + ';border-radius:2px;flex-shrink:0;"></div>'
            + " ".join(parts)
            + '</div>'
        )

    # Orange horizontal rule
    rule = (
        '<div style="width:100%;height:2px;background:linear-gradient(270deg,' + ACCENT + ',transparent);'
        'margin-bottom:48px;"></div>'
    )

    # Main text block (merged headline + detail)
    # Font size adapts to text length
    text_len = len(full_text)
    if text_len < 40:
        fs = 110
    elif text_len < 70:
        fs = 90
    elif text_len < 100:
        fs = 76
    else:
        fs = 64

    main_text = (
        '<div style="transform:translateY(' + str(h_y) + 'px);opacity:' + str(h_op) + ';transition:none;">'
        + badge_line
        + rule
        + '<div style="font-size:' + str(fs) + 'px;font-weight:900;color:#fff;'
        'line-height:1.3;text-align:right;letter-spacing:-0.5px;">'
        + vis_text + '</div>'
        '</div>'
    )

    # Bar chart below (fades in after text)
    bars_html = ""
    if bars:
        bars_html = (
            '<div style="margin-top:48px;transform:translateY(' + str(d_y) + 'px);opacity:' + str(d_op) + ';">'
            + _bar_chart_html(bars, opacity=bars_op)
            + '</div>'
        )

    return (
        "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>"
        + cairo_css + css_base + "</style></head><body>"
        + top_bar
        + ghost_num
        # Main layout — vertical centered
        + '<div style="position:absolute;top:0;left:0;right:0;bottom:0;'
        'display:flex;flex-direction:column;justify-content:center;'
        'padding:160px 80px 160px;">'
        + main_text
        + bars_html
        + '</div>'
        # Footer
        + '<div style="position:absolute;bottom:70px;left:80px;right:80px;'
        'display:flex;justify-content:space-between;align-items:center;">'
        '<span style="font-size:24px;color:rgba(255,255,255,0.2);letter-spacing:2px;max-width:600px;'
        'overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">' + footer_label + '</span>'
        '<span style="font-size:24px;font-weight:700;color:rgba(255,255,255,0.25);">' + counter_str + '</span>'
        '</div>'
        "</body></html>"
    )


# ── Slide transition — flash + horizontal push ────────────────────────────────
def _make_transition(img_a: Image.Image, img_b: Image.Image, n: int = 14) -> List[np.ndarray]:
    frames = []
    w, h = img_a.width, img_a.height
    # Brief white flash at midpoint for cinematic feel
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


# ── Core: single browser session ─────────────────────────────────────────────
async def _render_all_slides(
    slides_data: List[Dict[str, Any]],
    cairo_css: str,
    fps: int = 30,
    enter_sec: float = 0.7,
    hold_sec: float = 2.5,
) -> List[List[np.ndarray]]:
    from playwright.async_api import async_playwright
    from io import BytesIO

    ENTER_FRAMES = int(enter_sec * fps)
    HOLD_FRAMES  = int(hold_sec * fps)

    ENTER_STEPS = 12   # distinct entrance keyframes
    HOLD_STEPS  = 6    # distinct hold keyframes (progress bar)

    all_slide_frames: List[List[np.ndarray]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page(viewport={"width": 1080, "height": 1920})

        for s_idx, slide in enumerate(slides_data):
            enter_cache: List[np.ndarray] = []
            for step in range(ENTER_STEPS + 1):
                reveal = (step / ENTER_STEPS) * 0.5  # 0→0.5 (entrance phase)
                pfill  = reveal / 0.5 * 0.35          # progress fills to 0.35 during entrance
                html   = _slide_html(slide, cairo_css, reveal=reveal, pfill=pfill)
                await page.set_content(html, wait_until="domcontentloaded")
                png = await page.screenshot(full_page=False)
                enter_cache.append(np.array(Image.open(BytesIO(png)).convert("RGB")))

            hold_cache: List[np.ndarray] = []
            for step in range(HOLD_STEPS + 1):
                pfill = 0.35 + 0.65 * (step / HOLD_STEPS)  # 0.35→1.0
                html  = _slide_html(slide, cairo_css, reveal=1.0, pfill=pfill)
                await page.set_content(html, wait_until="domcontentloaded")
                png = await page.screenshot(full_page=False)
                hold_cache.append(np.array(Image.open(BytesIO(png)).convert("RGB")))

            # Build frame list
            slide_frames: List[np.ndarray] = []

            for f in range(ENTER_FRAMES):
                idx = min(int(f / ENTER_FRAMES * ENTER_STEPS), ENTER_STEPS)
                slide_frames.append(enter_cache[idx])

            for f in range(HOLD_FRAMES):
                idx = min(int(f / HOLD_FRAMES * HOLD_STEPS), HOLD_STEPS)
                slide_frames.append(hold_cache[idx])

            all_slide_frames.append(slide_frames)

        await browser.close()

    return all_slide_frames


# ── Main render ───────────────────────────────────────────────────────────────
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

    all_slide_frames = await _render_all_slides(
        slides_data, CAIRO_FONT_CSS, fps=fps, enter_sec=0.7, hold_sec=2.5
    )

    all_frames: List[np.ndarray] = []
    prev_img: Optional[Image.Image] = None

    for s_frames in all_slide_frames:
        if prev_img is not None and s_frames:
            all_frames.extend(_make_transition(prev_img, Image.fromarray(s_frames[0]), n=14))
        all_frames.extend(s_frames)
        if s_frames:
            prev_img = Image.fromarray(s_frames[-1])

    timestamp    = int(time.time())
    out_filename = "video_" + str(content_item_id) + "_" + str(timestamp) + ".mp4"
    out_path     = OUTPUT_DIR / out_filename
    duration     = len(all_frames) / fps

    def make_frame(t):
        return all_frames[min(int(t * fps), len(all_frames) - 1)]

    clip = VideoClip(make_frame, duration=duration)
    clip.write_videofile(
        str(out_path), fps=fps, codec="libx264", audio=False,
        preset="fast", ffmpeg_params=["-crf", "18", "-pix_fmt", "yuv420p"],
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
    colors = [ACCENT, ACCENT2, "#00C9FF", "#a855f7", "#10b981"]
    pats   = re.findall(r'([^\n،,]+?)[\s:]+(\d+(?:\.\d+)?)\s*(%|من|\/\d+)?', text)
    for i, m in enumerate(pats[:4]):
        try:
            num  = float(m[1])
            unit = m[2] or ""
            pct  = min(num, 100) if "%" in unit else min(num * 10, 100)
            disp = m[1] + ("%" if "%" in unit else "")
            bars.append({"label": m[0].strip()[:30], "pct": round(pct),
                         "value": disp, "color": colors[i % len(colors)]})
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
            lines = [body[:150]] if body else []
        if hook:
            slides.append(base({
                "is_cover": True, "category": "ابدأ من هنا",
                "headline": hook[:150],
                "detail": cues[:80] if cues else "",
            }))
        for i, line in enumerate(lines[:7]):
            merged = line
            slides.append(base({
                "category": "نقطة", "label": str(i + 1),
                "headline": merged[:150], "detail": "",
                "bars": _extract_bars_from_text(line),
            }))
        if cta:
            slides.append(base({"category": "الآن", "label": "", "headline": cta[:150], "detail": ""}))

    elif content_type == "CAROUSEL":
        raw_slides = generated_content.get("slides", [])
        title      = generated_content.get("title", "")
        if title:
            slides.append(base({"is_cover": True, "category": "اكتشف", "headline": title[:150], "detail": ""}))
        for i, s in enumerate(raw_slides):
            heading = s.get("heading", "")
            body    = s.get("body", "")
            tips    = s.get("tips_list") or []
            detail  = tips[0] if tips else ""
            # Merge heading + first detail
            merged = heading + (" — " + detail if detail else "")
            slides.append(base({
                "category": "نقطة", "label": str(i + 1),
                "headline": merged[:150], "detail": "",
                "bars": _extract_bars_from_text(body) if body else [],
            }))

    elif content_type == "POST":
        post  = generated_content.get("unified_post", "")
        lines = [ln.strip() for ln in post.split("\n") if ln.strip()]
        for i, line in enumerate(lines[:7]):
            slides.append(base({"category": "بوست", "label": str(i + 1),
                                 "headline": line[:150], "detail": ""}))

    if not slides:
        slides = [base({"category": "محتوى", "label": "", "headline": "لا يوجد محتوى", "detail": ""})]

    # Outro slide
    if article_title:
        slides.append(base({
            "is_outro": True,
            "category": "اقرأ المقال كاملاً",
            "headline": article_title[:130],
            "detail": brand,
            "image_url": image_url,
        }))

    return slides
