"""
Video Renderer — Premium Slideshow MP4
Format: 1080×1920 (9:16 vertical — Reels/TikTok)
Features:
  - Dark premium background with gradient glow blobs
  - Typing animation (text reveals character by character)
  - Animated progress bar at top (fills during each slide)
  - Bar charts for numeric comparisons
  - Outro slide with article image + title
  - Article title in footer, no clutter emojis
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


# ── Easing ────────────────────────────────────────────────────────────────────
def _ease_in_out_cubic(t: float) -> float:
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2


# ── Segmented progress bar (animates fill within current segment) ─────────────
def _progress_bar_html(current: int, total: int, fill: float) -> str:
    """
    Horizontal segmented bar at top.
    current: 1-based index of active segment
    fill: 0.0–1.0 how much of the current segment is filled
    """
    n = min(total, 12)
    parts = []
    gap = 6
    for i in range(n):
        seg = i + 1
        if seg < current:
            # completed
            inner = (
                '<div style="position:absolute;top:0;left:0;right:0;bottom:0;'
                'background:linear-gradient(90deg,#6366f1,#a855f7);border-radius:3px;"></div>'
            )
        elif seg == current:
            pct = round(fill * 100, 1)
            inner = (
                '<div style="position:absolute;top:0;left:0;bottom:0;'
                'width:' + str(pct) + '%;'
                'background:linear-gradient(90deg,#6366f1,#a855f7);border-radius:3px;'
                'box-shadow:0 0 10px rgba(99,102,241,0.8);"></div>'
            )
        else:
            inner = ""
        parts.append(
            '<div style="flex:1;height:6px;background:rgba(255,255,255,0.1);'
            'border-radius:3px;position:relative;overflow:hidden;">'
            + inner + "</div>"
        )
    return (
        '<div style="display:flex;gap:' + str(gap) + 'px;align-items:center;flex:1;">'
        + "".join(parts)
        + "</div>"
    )


# ── Bar chart ─────────────────────────────────────────────────────────────────
def _bar_chart_html(bars: List[Dict], opacity: float = 1.0) -> str:
    if not bars:
        return ""
    colors = ["#6366f1", "#a855f7", "#ec4899", "#f59e0b", "#10b981"]
    rows = ""
    for i, bar in enumerate(bars[:5]):
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
            "</div>"
            "</div>"
        )
    return (
        '<div style="width:100%;display:flex;flex-direction:column;gap:18px;opacity:'
        + str(round(opacity, 2)) + ';">' + rows + "</div>"
    )


# ── Slide HTML builder ────────────────────────────────────────────────────────
def _slide_html(
    slide: dict,
    cairo_css: str,
    reveal_ratio: float = 1.0,
    progress_fill: float = 1.0,
) -> str:
    """
    reveal_ratio 0→1: text types in
    progress_fill 0→1: current progress bar segment fills
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

    # Progress bar
    prog_html = _progress_bar_html(current, total, progress_fill)
    counter   = str(current) + " / " + str(total)

    # Typing reveal
    if reveal_ratio < 1.0:
        chars = max(1, int(len(headline) * reveal_ratio))
        vis_headline = headline[:chars]
        cursor = '<span style="color:#6366f1;font-weight:300;">|</span>'
    else:
        vis_headline = headline
        cursor = ""

    # Detail reveal (only after headline done)
    detail_alpha = max(0.0, (reveal_ratio - 0.8) / 0.2) if detail else 0.0
    if detail_alpha < 1.0 and detail:
        chars_d = max(0, int(len(detail) * detail_alpha))
        vis_detail = detail[:chars_d]
    else:
        vis_detail = detail

    # Bars appear after 0.7
    bars_opacity = min(1.0, max(0.0, (reveal_ratio - 0.7) / 0.3)) if bars else 0.0

    footer_right = article_title or brand

    # ── OUTRO SLIDE (image + title) ──────────────────────────────────────────
    if is_outro:
        img_block = ""
        if image_url:
            img_block = (
                '<div style="width:100%;height:420px;border-radius:28px;overflow:hidden;'
                'box-shadow:0 20px 60px rgba(0,0,0,0.5);margin-bottom:32px;">'
                '<img src="' + image_url + '" '
                'style="width:100%;height:100%;object-fit:cover;" />'
                "</div>"
            )
        card_body = (
            '<div style="display:flex;flex-direction:column;align-items:center;gap:24px;width:100%;">'
            + img_block
            + '<div style="font-size:34px;font-weight:700;color:rgba(255,255,255,0.45);">'
            + category + "</div>"
            + '<div style="font-size:80px;font-weight:900;color:#fff;text-align:center;line-height:1.25;">'
            + vis_headline + cursor + "</div>"
            + '<div style="width:80px;height:4px;background:linear-gradient(90deg,#6366f1,#a855f7);border-radius:2px;margin-top:8px;"></div>'
            + '<div style="font-size:34px;font-weight:600;color:rgba(255,255,255,0.5);text-align:center;">'
            + vis_detail + "</div>"
            + "</div>"
        )
        card_html = (
            '<div style="width:880px;padding:60px 60px;'
            'display:flex;flex-direction:column;align-items:center;">'
            + card_body + "</div>"
        )

    # ── COVER SLIDE ──────────────────────────────────────────────────────────
    elif is_cover:
        detail_block = ""
        if vis_detail:
            detail_block = (
                '<div style="font-size:38px;color:rgba(255,255,255,0.55);text-align:center;line-height:1.5;max-width:700px;">'
                + vis_detail + "</div>"
            )
        card_body = (
            '<div style="display:flex;flex-direction:column;align-items:center;gap:36px;width:100%;">'
            + '<div style="width:120px;height:4px;background:linear-gradient(90deg,#6366f1,#a855f7);border-radius:2px;"></div>'
            + '<div style="font-size:40px;font-weight:700;color:rgba(255,255,255,0.4);letter-spacing:3px;">' + (category or "") + "</div>"
            + '<div style="font-size:88px;font-weight:900;color:#fff;text-align:center;line-height:1.2;text-shadow:0 4px 30px rgba(0,0,0,0.5);">'
            + vis_headline + cursor + "</div>"
            + detail_block
            + "</div>"
        )
        card_html = (
            '<div style="width:880px;padding:80px 60px;'
            'display:flex;flex-direction:column;align-items:center;">'
            + card_body + "</div>"
        )

    # ── NORMAL SLIDE ─────────────────────────────────────────────────────────
    else:
        # Badge row (only if category/label exist, no emojis)
        badge_row = ""
        if category or label:
            badges = ""
            if category:
                badges += (
                    '<div style="background:rgba(99,102,241,0.2);border:1px solid rgba(99,102,241,0.45);'
                    'color:#a5b4fc;padding:8px 24px;border-radius:40px;font-size:28px;font-weight:700;">'
                    + category + "</div>"
                )
            if label:
                badges += (
                    '<div style="background:rgba(168,85,247,0.15);border:1px solid rgba(168,85,247,0.35);'
                    'color:#d8b4fe;padding:8px 24px;border-radius:40px;font-size:28px;font-weight:700;">'
                    + label + "</div>"
                )
            badge_row = (
                '<div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:flex-end;">'
                + badges + "</div>"
            )

        # Detail box (only for key stat)
        detail_block = ""
        if vis_detail:
            detail_block = (
                '<div style="background:rgba(255,255,255,0.05);border-right:3px solid #6366f1;'
                'border-radius:0 16px 16px 0;padding:22px 28px;width:100%;text-align:right;">'
                '<span style="font-size:32px;color:rgba(255,255,255,0.6);line-height:1.6;">'
                + vis_detail + "</span></div>"
            )

        bars_block = _bar_chart_html(bars, opacity=bars_opacity) if bars else ""

        card_body = (
            '<div style="display:flex;flex-direction:column;align-items:flex-end;gap:28px;width:100%;">'
            # Number (big faded) + small divider line
            + '<div style="display:flex;align-items:flex-start;justify-content:space-between;width:100%;">'
            + '<div style="font-size:180px;font-weight:900;color:rgba(255,255,255,0.06);line-height:1;" dir="ltr">' + number + "</div>"
            + '<div style="display:flex;flex-direction:column;align-items:flex-end;gap:12px;padding-top:16px;">'
            + '<div style="width:48px;height:4px;background:linear-gradient(90deg,#6366f1,#a855f7);border-radius:2px;"></div>'
            + "</div>"
            + "</div>"
            + badge_row
            # Headline — NO box, plain text
            + '<div style="font-size:72px;font-weight:900;color:#fff;line-height:1.3;text-align:right;width:100%;'
            'margin-top:-20px;">'
            + vis_headline + cursor + "</div>"
            + detail_block
            + bars_block
            + "</div>"
        )
        card_html = (
            '<div style="width:880px;background:rgba(255,255,255,0.03);'
            'border:1px solid rgba(255,255,255,0.08);border-radius:36px;padding:60px 56px;'
            'box-shadow:0 24px 72px rgba(0,0,0,0.35);">'
            + card_body + "</div>"
        )

    return (
        "<!DOCTYPE html>"
        '<html lang="ar" dir="rtl"><head><meta charset="UTF-8"><style>'
        + cairo_css
        + "* { margin:0; padding:0; box-sizing:border-box; font-family:'Cairo',sans-serif; }"
        + "html, body { width:1080px; height:1920px; overflow:hidden; }"
        + "body { background:linear-gradient(145deg,#0a0a14 0%,#12102a 45%,#0a1018 100%);"
        + "display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative; }"
        + "body::before { content:'';position:absolute;top:-150px;right:-150px;"
        + "width:650px;height:650px;"
        + "background:radial-gradient(circle,rgba(99,102,241,0.16) 0%,transparent 70%);pointer-events:none; }"
        + "body::after { content:'';position:absolute;bottom:-150px;left:-150px;"
        + "width:650px;height:650px;"
        + "background:radial-gradient(circle,rgba(168,85,247,0.12) 0%,transparent 70%);pointer-events:none; }"
        + "</style></head><body>"
        # Top accent line
        + '<div style="position:absolute;top:0;left:0;right:0;height:3px;'
        'background:linear-gradient(90deg,#6366f1,#a855f7,#ec4899);z-index:20;"></div>'
        # Progress bar row
        + '<div style="position:absolute;top:60px;left:60px;right:60px;'
        'display:flex;align-items:center;gap:20px;z-index:10;">'
        + prog_html
        + '<span style="font-size:26px;color:rgba(255,255,255,0.3);font-weight:600;white-space:nowrap;">'
        + counter + "</span></div>"
        # Main content
        + '<div style="position:relative;z-index:5;display:flex;flex-direction:column;'
        'align-items:center;justify-content:center;width:100%;padding:160px 0 160px;">'
        + card_html + "</div>"
        # Footer
        + '<div style="position:absolute;bottom:60px;left:60px;right:60px;'
        'display:flex;justify-content:space-between;align-items:center;'
        'border-top:1px solid rgba(255,255,255,0.06);padding-top:28px;z-index:10;">'
        + '<span style="font-size:26px;color:rgba(255,255,255,0.25);">احفظه</span>'
        + '<span style="font-size:26px;font-weight:700;color:rgba(255,255,255,0.5);'
        'max-width:700px;text-align:left;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">'
        + footer_right + "</span></div>"
        + "</body></html>"
    )


# ── Playwright render ─────────────────────────────────────────────────────────
async def _render_png(html: str, output_path: Path):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(path=str(output_path), full_page=False)
        await browser.close()


# ── Slide transition ──────────────────────────────────────────────────────────
def _make_transition(
    img_a: Image.Image, img_b: Image.Image, n: int = 18
) -> List[np.ndarray]:
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


# ── Render one slide as frames (typing + progress bar animation) ──────────────
async def _render_slide_frames(
    slide: dict,
    cairo_css: str,
    tmp_dir: Path,
    slide_idx: int,
    fps: int = 30,
    type_sec: float = 0.9,
    hold_sec: float = 2.4,
) -> List[np.ndarray]:
    """
    Generates frames for one slide:
    - type_sec: text types in, progress bar fills from 0→0.4
    - hold_sec: text full, progress bar continues 0.4→1.0
    """
    total_frames = int((type_sec + hold_sec) * fps)
    type_frames  = int(type_sec * fps)
    hold_frames  = total_frames - type_frames

    headline = slide.get("headline", "")
    n_steps  = max(10, len(headline) // 3)

    # Build keyframe ratios
    key_ratios = sorted(set(
        [round(s / n_steps, 3) for s in range(n_steps + 1)] + [1.0]
    ))

    # Render keyframes at reveal_ratio × progress_fill combos
    # During typing: reveal 0→1, progress 0→0.4
    # During hold:   reveal 1,   progress 0.4→1.0
    cache: Dict[str, np.ndarray] = {}

    async def get_frame(reveal: float, pfill: float, key: str):
        png = tmp_dir / ("f_" + str(slide_idx) + "_" + key + ".png")
        html = _slide_html(slide, cairo_css, reveal_ratio=reveal, progress_fill=pfill)
        await _render_png(html, png)
        arr = np.array(Image.open(str(png)).convert("RGB"))
        try:
            png.unlink()
        except Exception:
            pass
        cache[key] = arr

    # Typing keyframes
    for r in key_ratios:
        pfill = r * 0.4  # 0→0.4 during typing
        await get_frame(r, pfill, "t" + str(int(r * 1000)).zfill(4))

    # Hold keyframes (reveal=1, progress 0.4→1.0 in steps)
    hold_steps = 8
    for s in range(hold_steps + 1):
        pfill = 0.4 + 0.6 * (s / hold_steps)
        await get_frame(1.0, round(pfill, 3), "h" + str(s).zfill(3))

    # Build frame list
    frames_out: List[np.ndarray] = []

    # Typing phase
    for f in range(type_frames):
        r = f / max(type_frames - 1, 1)
        nearest_r = min(key_ratios, key=lambda x: abs(x - r))
        frames_out.append(cache["t" + str(int(nearest_r * 1000)).zfill(4)])

    # Hold phase
    hold_key_list = ["h" + str(s).zfill(3) for s in range(hold_steps + 1)]
    for f in range(hold_frames):
        idx = min(int(f / max(hold_frames - 1, 1) * hold_steps), hold_steps)
        frames_out.append(cache[hold_key_list[idx]])

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
        slide["total"]   = total
        slide["current"] = idx + 1

        slide_frames = await _render_slide_frames(
            slide, CAIRO_FONT_CSS, tmp_dir, idx, fps=fps,
            type_sec=0.9, hold_sec=2.4,
        )

        # Transition from previous slide
        if prev_img is not None and slide_frames:
            next_img = Image.fromarray(slide_frames[0])
            transition = _make_transition(prev_img, next_img, n=18)
            all_frames.extend(transition)

        all_frames.extend(slide_frames)

        if slide_frames:
            prev_img = Image.fromarray(slide_frames[-1])

    # Write MP4
    out_filename = "video_" + str(content_item_id) + "_" + str(timestamp) + ".mp4"
    out_path = OUTPUT_DIR / out_filename
    total_duration = len(all_frames) / fps

    def make_frame(t):
        return all_frames[min(int(t * fps), len(all_frames) - 1)]

    clip = VideoClip(make_frame, duration=total_duration)
    clip.write_videofile(
        str(out_path), fps=fps, codec="libx264", audio=False,
        preset="fast", ffmpeg_params=["-crf", "20", "-pix_fmt", "yuv420p"],
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


# ── Extract bars from text ────────────────────────────────────────────────────
def _extract_bars_from_text(text: str) -> List[Dict]:
    import re
    bars = []
    colors = ["#6366f1", "#a855f7", "#ec4899", "#f59e0b", "#10b981", "#3b82f6"]
    pattern = re.findall(r'([^\n،,]+?)[\s:]+(\d+(?:\.\d+)?)\s*(%|من|\/\d+)?', text)
    for i, match in enumerate(pattern[:5]):
        try:
            label_raw = match[0].strip()[:30]
            num_val = float(match[1])
            unit = match[2] or ""
            if "%" in unit:
                pct = min(num_val, 100)
                display_val = match[1] + "%"
            else:
                pct = min(num_val * 10, 100)
                display_val = match[1]
            bars.append({
                "label": label_raw,
                "pct": round(pct),
                "value": display_val,
                "color": colors[i % len(colors)],
            })
        except (ValueError, IndexError):
            continue
    return bars


# ── Content item → slides ────────────────────────────────────────────────────
def content_item_to_slides(
    generated_content: dict,
    content_type: str,
    brand: str = "غرفة المحتوى",
    article_title: str = "",
    image_url: str = "",
) -> List[Dict[str, Any]]:
    slides: List[Dict[str, Any]] = []

    def base(extra: dict) -> dict:
        return {
            "brand": brand,
            "article_title": article_title,
            "bars": [],
            **extra,
        }

    if content_type == "VIDEO_SCRIPT":
        hook = generated_content.get("hook", "")
        body = generated_content.get("body", "")
        cta  = generated_content.get("call_to_action", "")
        cues = generated_content.get("visual_cues", "")

        lines = [
            ln.strip().lstrip("-•* ").strip()
            for ln in body.split("\n") if ln.strip()
        ]
        if not lines:
            lines = [body[:120]] if body else []

        if hook:
            slides.append(base({
                "is_cover": True,
                "category": "ابدأ من هنا",
                "label": "",
                "headline": hook[:130],
                "detail": cues[:100] if cues else "",
            }))
        for i, line in enumerate(lines[:6]):
            slides.append(base({
                "category": "نقطة",
                "label": str(i + 1),
                "headline": line[:110],
                "detail": "",
                "bars": _extract_bars_from_text(line),
            }))
        if cta:
            slides.append(base({
                "category": "الآن",
                "label": "",
                "headline": cta[:110],
                "detail": "",
            }))

    elif content_type == "CAROUSEL":
        raw_slides = generated_content.get("slides", [])
        title = generated_content.get("title", "")

        if title:
            slides.append(base({
                "is_cover": True,
                "category": "اكتشف",
                "label": "",
                "headline": title[:130],
                "detail": "",
            }))

        for i, s in enumerate(raw_slides):
            heading = s.get("heading", "")
            body    = s.get("body", "")
            tips    = s.get("tips_list") or []
            detail  = tips[0] if tips else body[:100]
            slides.append(base({
                "category": "نقطة",
                "label": str(i + 1),
                "headline": heading[:110],
                "detail": detail,
                "bars": _extract_bars_from_text(body) if body else [],
            }))

    elif content_type == "POST":
        post  = generated_content.get("unified_post", "")
        lines = [ln.strip() for ln in post.split("\n") if ln.strip()]
        for i, line in enumerate(lines[:6]):
            slides.append(base({
                "category": "بوست",
                "label": str(i + 1),
                "headline": line[:110],
                "detail": "",
            }))

    if not slides:
        slides = [base({
            "category": "محتوى",
            "label": "",
            "headline": "لا يوجد محتوى",
            "detail": "",
        })]

    # Outro slide (image + article title)
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
