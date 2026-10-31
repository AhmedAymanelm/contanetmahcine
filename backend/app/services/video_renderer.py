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
ACCENT3  = "#7C3AED"   # purple accent
BG       = "#080810"   # near-black with subtle blue tint

# ── Author avatar (cached base64) ─────────────────────────────────────────────
_author_img_b64 = None
def _get_author_img_b64() -> str:
    global _author_img_b64
    if _author_img_b64:
        return _author_img_b64
    import os, base64
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate_paths = [
        os.path.join(base_dir, "static", "assets", "author_mic.jpg"),
        os.path.join(base_dir, "..", "backend", "static", "assets", "author_mic.jpg"),
        os.path.join(base_dir, "..", "static", "assets", "author_mic.jpg"),
        "/app/backend/static/assets/author_mic.jpg",
        "/app/static/assets/author_mic.jpg",
    ]
    for p in candidate_paths:
        try:
            if os.path.exists(p):
                with open(p, "rb") as f:
                    _author_img_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")
                    return _author_img_b64
        except Exception:
            pass
    _author_img_b64 = ""
    return _author_img_b64


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
    Premium editorial video slide — cinema-grade design.
    reveal: 0-0.5 = entrance (slide-up + scale), 0.5-1 = hold
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
    brand       = slide.get("brand", "zayedtech")
    author_name = slide.get("author_name", "د. زايد الحميري")
    article_title = slide.get("article_title", "")
    is_cover  = slide.get("is_cover", False)
    is_outro  = slide.get("is_outro", False)
    is_cta    = slide.get("is_cta", False)
    image_url = slide.get("image_url", "")

    top_bar = _top_bar_html(current, total, pfill)

    # Entrance animation
    ent_t    = min(1.0, reveal / 0.5)
    ent_ease = _ease_out_expo(ent_t)
    h_y   = int(80 * (1.0 - ent_ease))
    h_op  = round(ent_ease, 3)
    # Scale entrance: 0.92 -> 1.0
    h_scale = round(0.92 + 0.08 * ent_ease, 3)

    # Detail appears after headline
    d_t    = min(1.0, max(0.0, (reveal - 0.2) / 0.4))
    d_ease = _ease_out_expo(d_t)
    d_y    = int(40 * (1.0 - d_ease))
    d_op   = round(d_ease, 3)

    bars_t  = min(1.0, max(0.0, (reveal - 0.35) / 0.35))
    bars_op = _ease_out_expo(bars_t)

    # Color palette rotation per slide for visual variety
    palette = [
        ("#FF5C00", "#FF8A3D", "#1a0a00"),  # orange
        ("#7C3AED", "#A78BFA", "#0f0520"),  # purple
        ("#00C9FF", "#36D1DC", "#001a22"),  # cyan
        ("#10B981", "#34D399", "#001a10"),  # emerald
        ("#F43F5E", "#FB7185", "#1a0510"),  # rose
        ("#EAB308", "#FDE047", "#1a1500"),  # gold
    ]
    pi = (current - 1) % len(palette)
    slide_accent, slide_accent_light, bg_tint = palette[pi]
    # Cover always uses orange, outro uses purple
    if is_cover:
        slide_accent, slide_accent_light, bg_tint = palette[0]
    elif is_outro:
        slide_accent, slide_accent_light, bg_tint = palette[1]

    # Override with selected visual template colors if provided
    bg_base = BG
    custom_c = slide.get("custom_colors")
    if custom_c:
        slide_accent = custom_c.get("accent") or slide_accent
        slide_accent_light = slide_accent
        bg_tint = custom_c.get("color2") or bg_tint
        bg_base = custom_c.get("color1") or bg_base

    css_base = (
        "* { margin:0; padding:0; box-sizing:border-box; font-family:'Cairo',sans-serif; }"
        "html, body { width:1080px; height:1920px; overflow:hidden; }"
        "body { background:" + bg_base + "; position:relative; overflow:hidden; }"
    )

    # ── Background gradient layers ────────────────────────────────────────
    bg_layers = (
        # Base dark gradient
        '<div style="position:absolute;inset:0;'
        'background:linear-gradient(160deg,' + bg_base + ' 0%,' + bg_tint + ' 50%,' + bg_base + ' 100%);"></div>'
        # Accent glow (top-right)
        '<div style="position:absolute;top:-300px;right:-200px;width:800px;height:800px;'
        'border-radius:50%;background:radial-gradient(circle,' + slide_accent + '12 0%,transparent 70%);'
        'pointer-events:none;"></div>'
        # Secondary glow (bottom-left)
        '<div style="position:absolute;bottom:-250px;left:-150px;width:600px;height:600px;'
        'border-radius:50%;background:radial-gradient(circle,' + slide_accent_light + '08 0%,transparent 60%);'
        'pointer-events:none;"></div>'
        # Noise texture overlay
        '<div style="position:absolute;inset:0;opacity:0.03;'
        'background-image:url(\'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%224%22 height=%224%22><rect width=%224%22 height=%224%22 fill=%22%23fff%22 fill-opacity=%220.04%22/></svg>\');'
        'background-repeat:repeat;pointer-events:none;"></div>'
    )

    # ── Slide counter dots (top area) ─────────────────────────────────────
    dots = ""
    for i in range(total):
        is_active = (i < current)
        is_current = (i == current - 1)
        dot_w = "40px" if is_current else "12px"
        dot_bg = ("linear-gradient(90deg," + slide_accent + "," + slide_accent_light + ")") if is_active else "rgba(255,255,255,0.15)"
        dots += (
            '<div style="width:' + dot_w + ';height:5px;border-radius:3px;'
            'background:' + dot_bg + ';transition:all 0.3s;'
            + ('box-shadow:0 0 12px ' + slide_accent + '88;' if is_current else '') +
            '"></div>'
        )
    dot_bar = (
        '<div style="position:absolute;top:60px;left:80px;right:80px;'
        'display:flex;gap:6px;align-items:center;justify-content:center;z-index:50;">'
        + dots + '</div>'
    )

    # ── OUTRO ─────────────────────────────────────────────────────────────
    if is_outro:
        overlay = ""
        if image_url:
            overlay = (
                '<div style="position:absolute;top:0;left:0;right:0;height:1080px;">'
                '<img src="' + image_url + '" style="width:100%;height:100%;object-fit:cover;"/>'
                '<div style="position:absolute;inset:0;'
                'background:linear-gradient(to bottom,transparent 0%,' + BG + 'ee 60%,' + BG + ' 100%);"></div>'
                '</div>'
            )
        content = (
            '<div style="position:absolute;bottom:320px;left:80px;right:80px;'
            'transform:translateY(' + str(h_y) + 'px) scale(' + str(h_scale) + ');opacity:' + str(h_op) + ';">'
            # Accent label
            '<div style="display:inline-block;padding:8px 24px;border-radius:8px;'
            'background:' + slide_accent + ';margin-bottom:36px;">'
            '<span style="font-size:24px;font-weight:800;color:#fff;letter-spacing:2px;">'
            + (category or "اقرأ المقال") + '</span></div>'
            # Title
            '<div style="font-size:72px;font-weight:900;color:#fff;line-height:1.2;text-align:right;'
            'text-shadow:0 4px 40px rgba(0,0,0,0.6);">'
            + headline[:130] + '</div>'
            # Brand line
            '<div style="margin-top:40px;display:flex;align-items:center;gap:16px;justify-content:flex-end;">'
            '<div style="width:40px;height:3px;background:' + slide_accent + ';border-radius:2px;"></div>'
            '<span style="font-size:28px;font-weight:700;color:' + slide_accent + ';">' + brand + '</span>'
            '</div></div>'
        )
        return (
            "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>"
            + cairo_css + css_base + "</style></head><body>"
            + bg_layers + top_bar + dot_bar + overlay + content
            + "</body></html>"
        )

    # ── COVER ─────────────────────────────────────────────────────────────
    elif is_cover:
        content = (
            '<div style="position:absolute;inset:0;display:flex;flex-direction:column;'
            'justify-content:center;align-items:center;padding:100px 80px;">'
            # Decorative ring
            '<div style="width:200px;height:200px;border-radius:50%;'
            'border:3px solid ' + slide_accent + '33;position:relative;margin-bottom:60px;'
            'transform:scale(' + str(h_scale) + ');opacity:' + str(h_op) + ';">'
            '<div style="position:absolute;inset:20px;border-radius:50%;'
            'background:linear-gradient(135deg,' + slide_accent + '22,' + slide_accent_light + '11);'
            'display:flex;align-items:center;justify-content:center;">'
            '<span style="font-size:80px;font-weight:900;color:' + slide_accent + ';">' + number + '</span>'
            '</div></div>'
            # Headline
            '<div style="transform:translateY(' + str(h_y) + 'px);opacity:' + str(h_op) + ';text-align:center;">'
            '<div style="font-size:96px;font-weight:900;color:#fff;line-height:1.15;'
            'letter-spacing:-2px;text-shadow:0 4px 60px rgba(0,0,0,0.4);">'
            + headline[:120] + '</div>'
            # Accent underline
            '<div style="width:120px;height:5px;border-radius:3px;margin:48px auto 0;'
            'background:linear-gradient(90deg,' + slide_accent + ',' + slide_accent_light + ');'
            'box-shadow:0 0 24px ' + slide_accent + '66;"></div>'
            '</div></div>'
        )
        return (
            "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>"
            + cairo_css + css_base + "</style></head><body>"
            + bg_layers + top_bar + dot_bar + content
            # Footer brand
            + '<div style="position:absolute;bottom:80px;left:80px;right:80px;text-align:center;">'
            '<span style="font-size:24px;color:rgba(255,255,255,0.2);letter-spacing:4px;">'
            + (article_title or brand) + '</span></div>'
            + "</body></html>"
        )

    # ── CTA SLIDE (last slide with author avatar) ─────────────────────────
    elif is_cta:
        author_img = _get_author_img_b64()
        avatar_html = ""
        if author_img:
            avatar_html = (
                '<div style="width:260px;height:260px;border-radius:50%;overflow:hidden;'
                'border:8px solid ' + slide_accent + ';'
                'box-shadow:0 0 50px ' + slide_accent + '55, 0 20px 60px rgba(0,0,0,0.6);'
                'transform:scale(' + str(h_scale) + ');opacity:' + str(h_op) + ';flex-shrink:0;">'
                '<img src="' + author_img + '" style="width:100%;height:100%;object-fit:cover;object-position:35% 10%;" />'
                '</div>'
            )

        author_info_html = (
            '<div style="transform:translateY(' + str(h_y) + 'px);opacity:' + str(h_op) + ';text-align:center;margin-top:20px;">'
            '<div style="font-size:44px;font-weight:900;color:#ffffff;letter-spacing:-0.5px;">' + author_name + '</div>'
            '<div style="font-size:24px;font-weight:700;color:' + slide_accent + ';margin-top:4px;letter-spacing:1px;" dir="ltr">@' + brand + '</div>'
            '</div>'
        )

        category_pill = (
            '<div style="margin-top:28px;transform:translateY(' + str(h_y) + 'px);opacity:' + str(h_op) + ';">'
            '<div style="display:inline-block;padding:8px 28px;border-radius:30px;'
            'background:' + slide_accent + '22;border:1.5px solid ' + slide_accent + ';">'
            '<span style="font-size:24px;font-weight:800;color:' + slide_accent + ';">' + (category or "شاركنا رأيك") + '</span>'
            '</div></div>'
        )

        headline_html = (
            '<div style="transform:translateY(' + str(h_y) + 'px);opacity:' + str(h_op) + ';text-align:center;margin-top:20px;max-width:920px;">'
            '<div style="font-size:60px;font-weight:900;color:#fff;line-height:1.25;letter-spacing:-1px;'
            'text-shadow:0 4px 30px rgba(0,0,0,0.5);">'
            + headline[:130] + '</div>'
            '</div>'
        )

        detail_text = detail or "اكتب رأيك في التعليقات 👇"
        detail_html = (
            '<div style="margin-top:24px;padding:12px 32px;border-radius:12px;'
            'background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);'
            'transform:translateY(' + str(d_y) + 'px);opacity:' + str(d_op) + ';">'
            '<span style="font-size:26px;font-weight:600;color:rgba(255,255,255,0.7);">'
            + detail_text + '</span></div>'
        )

        follow_btn = (
            '<div style="margin-top:32px;transform:translateY(' + str(d_y) + 'px);opacity:' + str(d_op) + ';">'
            '<div style="display:inline-flex;align-items:center;gap:12px;'
            'background:linear-gradient(135deg,' + slide_accent + ',' + slide_accent_light + ');'
            'color:#fff;padding:14px 44px;border-radius:50px;'
            'font-size:28px;font-weight:800;box-shadow:0 12px 35px ' + slide_accent + '55;">'
            '<span>+ تابع</span>'
            '<span dir="ltr">@' + brand + '</span>'
            '</div></div>'
        )

        content = (
            '<div style="position:absolute;inset:0;display:flex;flex-direction:column;'
            'justify-content:center;align-items:center;padding:100px 80px;">'
            + avatar_html
            + author_info_html
            + category_pill
            + headline_html
            + detail_html
            + follow_btn
            + '</div>'
        )
        return (
            "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>"
            + cairo_css + css_base + "</style></head><body>"
            + bg_layers + top_bar + dot_bar + content
            + "</body></html>"
        )

    # ── NORMAL SLIDE ──────────────────────────────────────────────────────

    # Font size — adaptive to text length (shorter = bigger = better)
    text_len = len(headline)
    if text_len < 25:
        fs = 120
    elif text_len < 40:
        fs = 100
    elif text_len < 60:
        fs = 82
    elif text_len < 80:
        fs = 68
    else:
        fs = 56

    # Note/stat display — big accent number if it contains digits
    note_html = ""
    if detail:
        import re as _re
        has_number = bool(_re.search(r'\d', detail))
        if has_number:
            # Extract number and text parts
            num_match = _re.search(r'[\d,.٪%]+', detail)
            num_str = num_match.group(0) if num_match else ""
            rest_text = detail.replace(num_str, "").strip() if num_str else detail
            note_html = (
                '<div style="margin-top:56px;transform:translateY(' + str(d_y) + 'px);opacity:' + str(d_op) + ';">'
                '<div style="display:flex;align-items:baseline;gap:20px;justify-content:center;">'
                '<span style="font-size:96px;font-weight:900;color:' + slide_accent + ';'
                'letter-spacing:-3px;text-shadow:0 0 40px ' + slide_accent + '44;">' + num_str + '</span>'
                + ('<span style="font-size:32px;font-weight:600;color:rgba(255,255,255,0.5);">' + rest_text + '</span>' if rest_text else '') +
                '</div></div>'
            )
        else:
            note_html = (
                '<div style="margin-top:44px;transform:translateY(' + str(d_y) + 'px);opacity:' + str(d_op) + ';">'
                '<div style="padding:12px 32px;border-radius:12px;background:rgba(255,255,255,0.06);'
                'border:1px solid rgba(255,255,255,0.08);display:inline-block;">'
                '<span style="font-size:30px;font-weight:600;color:rgba(255,255,255,0.6);">' + detail + '</span>'
                '</div></div>'
            )

    # Bar chart
    bars_html = ""
    if bars:
        bars_html = (
            '<div style="margin-top:56px;transform:translateY(' + str(d_y) + 'px);opacity:' + str(d_op) + ';">'
            + _bar_chart_html(bars, opacity=bars_op)
            + '</div>'
        )

    # Category pill
    cat_html = ""
    if category:
        cat_html = (
            '<div style="display:inline-block;padding:6px 20px;border-radius:20px;'
            'background:' + slide_accent + '18;border:1px solid ' + slide_accent + '33;margin-bottom:28px;">'
            '<span style="font-size:22px;font-weight:700;color:' + slide_accent + ';letter-spacing:2px;">'
            + category + '</span></div>'
        )

    # Slide number — small accent label
    num_label = ""
    if label:
        num_label = (
            '<div style="margin-bottom:20px;opacity:0.5;">'
            '<span style="font-size:120px;font-weight:900;color:' + slide_accent + '15;'
            'position:absolute;right:80px;top:50%;transform:translateY(-80%);pointer-events:none;">'
            + label.zfill(2) + '</span></div>'
        )

    # Accent vertical line decoration
    accent_line = (
        '<div style="position:absolute;right:65px;top:50%;transform:translateY(-50%);'
        'width:4px;height:200px;border-radius:2px;'
        'background:linear-gradient(to bottom,transparent,' + slide_accent + ',' + slide_accent_light + ',transparent);'
        'opacity:0.4;"></div>'
    )

    return (
        "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>"
        + cairo_css + css_base + "</style></head><body>"
        + bg_layers
        + top_bar
        + dot_bar
        + accent_line
        + num_label
        # Main content — centered
        + '<div style="position:absolute;inset:0;display:flex;flex-direction:column;'
        'justify-content:center;align-items:center;padding:180px 100px 180px 100px;">'
        # Category pill
        + '<div style="transform:translateY(' + str(h_y) + 'px) scale(' + str(h_scale) + ');opacity:' + str(h_op) + ';'
        'text-align:center;width:100%;">'
        + cat_html
        # Main text — CENTERED, big, bold
        + '<div style="font-size:' + str(fs) + 'px;font-weight:900;color:#fff;'
        'line-height:1.25;text-align:center;letter-spacing:-1px;'
        'text-shadow:0 4px 30px rgba(0,0,0,0.4);">'
        + headline + '</div>'
        + '</div>'
        # Note / stat below
        + '<div style="text-align:center;">'
        + note_html
        + bars_html
        + '</div>'
        + '</div>'
        # Footer
        + '<div style="position:absolute;bottom:70px;left:80px;right:80px;'
        'display:flex;justify-content:center;">'
        '<span style="font-size:22px;color:rgba(255,255,255,0.25);letter-spacing:2px;">'
        + author_name + ' · @' + brand + '</span></div>'
        + "</body></html>"
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
    brand: str = "zayedtech",
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
    brand: str = "zayedtech",
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
    brand: str = "zayedtech",
    author_name: str = "د. زايد الحميري",
    article_title: str = "",
    image_url: str = "",
) -> List[Dict[str, Any]]:
    slides: List[Dict[str, Any]] = []

    def base(extra: dict) -> dict:
        return {
            "brand": brand,
            "author_name": author_name,
            "article_title": article_title,
            "bars": [],
            **extra
        }

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
            slides.append(base({
                "is_cta": True,
                "category": "شاركنا رأيك",
                "label": "",
                "headline": cta[:150],
                "detail": "اكتب رأيك في التعليقات 👇",
            }))

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
            is_last = (i == len(raw_slides) - 1)
            if is_last:
                slides.append(base({
                    "is_cta": True,
                    "category": "شاركنا رأيك",
                    "label": "",
                    "headline": heading[:150] or "شاركنا رأيك",
                    "detail": body[:80] or detail[:80] or "اكتب رأيك في التعليقات 👇",
                }))
            else:
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

    elif content_type == "REEL":
        raw_slides = generated_content.get("slides", [])
        for i, s in enumerate(raw_slides):
            text = s.get("text", "")
            note = s.get("note", "") or ""
            is_first = (i == 0)
            is_last  = (i == len(raw_slides) - 1)
            slides.append(base({
                "is_cover": is_first,
                "is_cta": is_last,
                "category": "ابدأ" if is_first else ("شاركنا رأيك" if is_last else ""),
                "label": "" if (is_first or is_last) else str(i),
                "headline": text[:150],
                "detail": note[:80] if note else "",
                "bars": _extract_bars_from_text(text + " " + note) if (note and not is_last) else [],
            }))

    if not slides:
        slides = [base({"category": "محتوى", "label": "", "headline": "لا يوجد محتوى", "detail": ""})]

    # Outro slide — only for content types that don't already have their own closing CTA slide
    if article_title and content_type not in ("REEL", "VIDEO_SCRIPT"):
        slides.append(base({
            "is_outro": True,
            "category": "اقرأ المقال كاملاً",
            "headline": article_title[:130],
            "detail": brand,
            "image_url": image_url,
        }))

    return slides
