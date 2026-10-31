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


# ── Ministry of Community Empowerment Logo (cached base64) ──────────────────────
_ministry_logo_b64 = None
def _get_ministry_logo_b64() -> str:
    global _ministry_logo_b64
    if _ministry_logo_b64:
        return _ministry_logo_b64
    import os, base64
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate_paths = [
        "/Users/ahmed/UEA AGANTIC/content-machine/frontend/ministry_logo_transparent.png",
        str(Path(__file__).resolve().parents[3] / "frontend" / "ministry_logo_transparent.png"),
        os.path.join(base_dir, "static", "assets", "ministry_logo_transparent.png"),
        os.path.join(base_dir, "..", "backend", "static", "assets", "ministry_logo_transparent.png"),
        os.path.join(base_dir, "..", "static", "assets", "ministry_logo_transparent.png"),
        os.path.join(base_dir, "..", "frontend", "ministry_logo_transparent.png"),
        "/app/backend/static/assets/ministry_logo_transparent.png",
        "/app/frontend/ministry_logo_transparent.png",
        "/app/static/assets/ministry_logo_transparent.png",
    ]
    for p in candidate_paths:
        try:
            if os.path.exists(p):
                with open(p, "rb") as f:
                    _ministry_logo_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")
                    return _ministry_logo_b64
        except Exception:
            pass
    _ministry_logo_b64 = ""
    return _ministry_logo_b64


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


# ── Multi-Bar Comparison Dashboard ────────────────────────────────────────────
def _render_multi_bar_dashboard(bars: List[Dict], slide_accent: str, reveal: float, d_y: float, d_op: float) -> str:
    if not bars:
        return ""
    colors = [slide_accent, "#FFB700", "#00E5FF", "#10B981", "#A855F7"]
    rows = ""
    fill_factor = min(1.0, max(0.0, (reveal - 0.2) / 0.5))

    for i, bar in enumerate(bars[:4]):
        label = bar.get("label", "")
        pct   = max(5, min(100, bar.get("pct", 0)))
        anim_pct = round(pct * fill_factor, 1)
        color = bar.get("color", colors[i % len(colors)])
        val   = bar.get("value", f"{pct}%")
        mb    = 18 if i < min(len(bars), 4) - 1 else 0

        rows += (
            f'<div style="display:flex;flex-direction:column;gap:8px;margin-bottom:{mb}px;">'
            f'  <div style="display:flex;justify-content:space-between;align-items:center;">'
            f'    <div style="display:flex;align-items:center;gap:12px;">'
            f'      <div style="width:12px;height:12px;border-radius:50%;background:{color};box-shadow:0 0 14px {color};"></div>'
            f'      <span style="font-size:28px;font-weight:800;color:rgba(255,255,255,0.9);letter-spacing:-0.5px;">{label}</span>'
            f'    </div>'
            f'    <span style="font-size:36px;font-weight:900;color:{color};letter-spacing:-1px;text-shadow:0 0 25px {color}66;">{val}</span>'
            f'  </div>'
            f'  <div style="height:20px;background:rgba(0,0,0,0.6);border:1.5px solid rgba(255,255,255,0.1);border-radius:10px;padding:3px;overflow:visible;position:relative;box-shadow:inset 0 2px 6px rgba(0,0,0,0.8);">'
            f'    <div style="width:{anim_pct}%;height:100%;border-radius:6px;background:linear-gradient(90deg,{color},{color}dd);box-shadow:0 0 20px {color}88;position:relative;">'
            f'      <div style="position:absolute;left:-6px;top:50%;transform:translateY(-50%);width:16px;height:16px;border-radius:50%;background:#ffffff;box-shadow:0 0 12px #ffffff,0 0 20px {color};"></div>'
            f'    </div>'
            f'  </div>'
            f'</div>'
        )

    return (
        f'<div style="margin-top:40px;transform:translateY({d_y}px);opacity:{d_op};width:100%;max-width:880px;">'
        f'  <div style="background:linear-gradient(145deg,rgba(255,255,255,0.08) 0%,rgba(15,15,25,0.85) 100%);'
        f'              border:1.5px solid rgba(255,255,255,0.14);border-radius:32px;padding:32px 42px;'
        f'              box-shadow:0 25px 60px rgba(0,0,0,0.6),0 0 50px {slide_accent}25;backdrop-filter:blur(25px);">'
        f'    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid rgba(255,255,255,0.08);">'
        f'      <span style="font-size:24px;font-weight:800;color:rgba(255,255,255,0.6);letter-spacing:1px;">مؤشرات وبيانات مقارنة</span>'
        f'      <span style="display:inline-flex;align-items:center;gap:8px;font-size:18px;font-weight:800;color:{slide_accent};background:{slide_accent}18;padding:5px 16px;border-radius:20px;border:1px solid {slide_accent}33;">'
        f'        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{slide_accent};box-shadow:0 0 8px {slide_accent};"></span>بيانات مباشرة'
        f'      </span>'
        f'    </div>'
        f'    {rows}'
        f'  </div>'
        f'</div>'
    )


# ── Hero Single Stat HUD ──────────────────────────────────────────────────────
def _render_hero_stat_hud(stat_text: str, pct_val: Optional[float], slide_accent: str, slide_accent_light: str, reveal: float, d_y: float, d_op: float, headline: str = "", force_type: Optional[str] = None) -> str:
    import re
    # Extract numbers or percentages
    num_match = re.search(r'([+\-▲▼↗]?\s*[\d,.]+\s*(?:%|٪|x|X|k|K|M|B|تريليون|مليار|مليون)?)', stat_text)
    num_str = num_match.group(0).strip() if num_match else ""
    label_text = stat_text.replace(num_str, "").strip() if num_str else stat_text
    label_text = re.sub(r'^[،,:\-–]\s*', '', label_text).strip()

    combined_lower = (stat_text + " " + headline).lower()

    # Determine metric classification
    is_percentage = (force_type == "PERCENTAGE_BAR") or bool(re.search(r'[%٪]', stat_text + " " + num_str))
    is_tech_spec = (force_type == "TECH_SPEC") or bool(re.search(
        r'ميجابكسل|بكسل|هرتز|رام|جيجابايت|تيرابايت|مللي أمبير|واط|نانومتر|بوصة|إطار|عدسة|كاميرا|معالج|شاشة|بطارية|موبايل|هاتف|سماعة|سنابدراجون|أوليد|أمبوليد|fps|hz|mp|gb|tb|mah|nm|ghz|mhz|watt|snapdragon|oled|amoled',
        combined_lower
    ))
    is_financial = (force_type == "FINANCIAL_METRIC") or bool(re.search(
        r'مليار|تريليون|مليون دولار|دولار|درهم|ريال|جنيه|إنفاق|إيراد|أرباح|أرباحاً|استثمار|رأسمالي|قيمة سوقية|عائد',
        combined_lower
    ))

    if force_type == "FINANCIAL_METRIC":
        is_tech_spec = False
        is_percentage = False
    elif force_type == "TECH_SPEC":
        is_percentage = False
        is_financial = False
    elif force_type == "PERCENTAGE_BAR":
        is_tech_spec = False
        is_financial = False

    svg_id = abs(hash(stat_text)) % 100000
    visual_graphic_html = ""

    if is_percentage:
        if pct_val is None:
            clean_digits = re.search(r'[\d.]+', num_str)
            pct_val = min(100.0, float(clean_digits.group(0))) if clean_digits else 50.0

        is_upward = bool(re.search(r'نمو|زيادة|ارتفاع|قفزة|مضاعفة|صعود|ربح|أرباح|قياسي|تفوق', combined_lower))
        badge_text = "مؤشر قياسي" if is_upward else "إحصائية موثقة"
        badge_color = "#35D399" if is_upward else slide_accent
        header_title = label_text or "معدل الإنجاز"

        # ── PERCENTAGE PROGRESS BAR (Strict LTR: starts at 0% on left and expands to right) ──
        fill_pct = min(100.0, pct_val)
        anim_fill = round(fill_pct * min(1.0, max(0.0, (reveal - 0.2) / 0.5)), 1)
        
        svg_dash = 900
        dash_offset = round(svg_dash * (1.0 - min(1.0, max(0.0, (reveal - 0.25) / 0.45))))
        sparkline_svg = (
            f'<svg viewBox="0 0 800 120" style="width:100%;height:90px;margin-top:16px;overflow:visible;">'
            f'  <defs>'
            f'    <linearGradient id="hudGrad_{svg_id}" x1="0" y1="0" x2="0" y2="1">'
            f'      <stop offset="0%" stop-color="{slide_accent}" stop-opacity="0.38"/>'
            f'      <stop offset="100%" stop-color="{slide_accent}" stop-opacity="0.0"/>'
            f'    </linearGradient>'
            f'    <filter id="glow_{svg_id}" x="-20%" y="-20%" width="140%" height="140%">'
            f'      <feGaussianBlur stdDeviation="6" result="blur"/>'
            f'      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
            f'    </filter>'
            f'  </defs>'
            f'  <line x1="0" y1="35" x2="800" y2="35" stroke="rgba(255,255,255,0.06)" stroke-dasharray="6 6"/>'
            f'  <line x1="0" y1="80" x2="800" y2="80" stroke="rgba(255,255,255,0.06)" stroke-dasharray="6 6"/>'
            f'  <path d="M 0 110 C 180 105, 300 85, 450 60 C 580 40, 680 20, 790 10 L 790 120 L 0 120 Z" fill="url(#hudGrad_{svg_id})"/>'
            f'  <path d="M 0 110 C 180 105, 300 85, 450 60 C 580 40, 680 20, 790 10" fill="none" stroke="{slide_accent}" stroke-width="5" filter="url(#glow_{svg_id})" stroke-dasharray="{svg_dash}" stroke-dashoffset="{dash_offset}"/>'
            f'  <circle cx="790" cy="10" r="14" fill="{slide_accent}" opacity="0.4"/>'
            f'  <circle cx="790" cy="10" r="7" fill="#ffffff" filter="drop-shadow(0 0 12px {slide_accent})"/>'
            f'</svg>'
        )

        visual_graphic_html = (
            f'<div style="margin-top:20px;direction:ltr;text-align:left;">'
            f'  <div style="height:22px;background:rgba(0,0,0,0.65);border:1.5px solid rgba(255,255,255,0.12);'
            f'              border-radius:12px;padding:3px;position:relative;overflow:visible;'
            f'              box-shadow:inset 0 2px 8px rgba(0,0,0,0.8);direction:ltr;text-align:left;">'
            f'    <div style="width:{anim_fill}%;height:100%;border-radius:8px;'
            f'                background:linear-gradient(90deg,{slide_accent},#FFB700,#00E5FF);'
            f'                box-shadow:0 0 25px {slide_accent}, 0 0 10px #FFB700;'
            f'                position:relative;margin:0;float:left;">'
            f'      <div style="position:absolute;right:-9px;top:50%;transform:translateY(-50%);'
            f'                  width:22px;height:22px;border-radius:50%;background:#ffffff;'
            f'                  box-shadow:0 0 16px #ffffff,0 0 30px {slide_accent};"></div>'
            f'    </div>'
            f'  </div>'
            f'  <div style="display:flex;justify-content:space-between;margin-top:10px;font-family:monospace;'
            f'              font-size:16px;color:rgba(255,255,255,0.4);font-weight:700;direction:ltr;text-align:left;">'
            f'    <span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span>'
            f'  </div>'
            f'</div>'
            f'{sparkline_svg}'
        )

    elif is_tech_spec:
        # ── LUXURY KEYNOTE HARDWARE & TECH SPEC HUD ──
        badge_text = "مواصفات العتاد"
        badge_color = "#00E5FF"
        header_title = label_text or "المواصفات التقنية"

        is_camera = bool(re.search(r'ميجابكسل|بكسل|عدسة|كاميرا|mp', combined_lower))
        is_screen = bool(re.search(r'هرتز|شاشة|بوصة|hz|oled|amoled', combined_lower))
        is_battery = bool(re.search(r'بطارية|مللي أمبير|واط|mah|watt', combined_lower))

        if is_camera:
            visual_graphic_html = (
                f'<div style="margin-top:24px;padding:22px 28px;background:rgba(0,0,0,0.45);'
                f'            border:1.5px solid rgba(0,229,255,0.25);border-radius:24px;position:relative;'
                f'            box-shadow:inset 0 0 30px rgba(0,229,255,0.08);">'
                f'  <div style="display:flex;justify-content:space-between;align-items:center;gap:20px;">'
                f'    <div style="display:flex;align-items:center;gap:14px;">'
                f'      <div style="position:relative;width:56px;height:56px;border-radius:50%;border:2px solid #00E5FF;'
                f'                  display:flex;align-items:center;justify-content:center;box-shadow:0 0 25px rgba(0,229,255,0.4);">'
                f'        <div style="width:34px;height:34px;border-radius:50%;border:1.5px dashed rgba(255,255,255,0.5);background:rgba(0,229,255,0.15);"></div>'
                f'        <div style="position:absolute;width:12px;height:12px;border-radius:50%;background:#ffffff;box-shadow:0 0 12px #ffffff;"></div>'
                f'      </div>'
                f'      <div style="position:relative;width:56px;height:56px;border-radius:50%;border:2px solid {slide_accent};'
                f'                  display:flex;align-items:center;justify-content:center;box-shadow:0 0 25px {slide_accent}44;">'
                f'        <div style="width:34px;height:34px;border-radius:50%;border:1.5px dashed rgba(255,255,255,0.5);background:{slide_accent}15;"></div>'
                f'        <div style="position:absolute;width:12px;height:12px;border-radius:50%;background:#ffffff;box-shadow:0 0 12px #ffffff;"></div>'
                f'      </div>'
                f'      <div style="margin-right:6px;">'
                f'        <div style="font-size:20px;font-weight:900;color:#ffffff;letter-spacing:-0.3px;">نظام تصوير احترافي مزدوج</div>'
                f'        <div style="font-size:14px;color:rgba(255,255,255,0.55);margin-top:2px;">عدستان فائقة الدقة 50MP + 50MP</div>'
                f'      </div>'
                f'    </div>'
                f'    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">'
                f'      <div style="font-size:13px;font-weight:800;color:#00E5FF;padding:5px 14px;background:rgba(0,229,255,0.12);'
                f'                  border:1px solid rgba(0,229,255,0.3);border-radius:20px;font-family:monospace;letter-spacing:1px;">DUAL SENSOR OIS</div>'
                f'      <div style="font-size:13px;color:rgba(255,255,255,0.45);font-weight:600;">معالجة سينمائية بالذكاء الاصطناعي</div>'
                f'    </div>'
                f'  </div>'
                f'</div>'
            )
        elif is_screen:
            visual_graphic_html = (
                f'<div style="margin-top:24px;padding:22px 28px;background:rgba(0,0,0,0.45);'
                f'            border:1.5px solid rgba(0,229,255,0.25);border-radius:24px;position:relative;'
                f'            box-shadow:inset 0 0 30px rgba(0,229,255,0.08);">'
                f'  <div style="display:flex;justify-content:space-between;align-items:center;gap:20px;">'
                f'    <div style="display:flex;align-items:center;gap:14px;">'
                f'      <div style="width:52px;height:52px;border-radius:14px;border:2px solid #00E5FF;'
                f'                  display:flex;align-items:center;justify-content:center;background:rgba(0,229,255,0.1);box-shadow:0 0 25px rgba(0,229,255,0.35);">'
                f'        <span style="font-size:24px;font-weight:900;color:#00E5FF;font-family:monospace;">Hz</span>'
                f'      </div>'
                f'      <div>'
                f'        <div style="font-size:20px;font-weight:900;color:#ffffff;">شاشة ذات تردد تكيفي فائق</div>'
                f'        <div style="font-size:14px;color:rgba(255,255,255,0.55);margin-top:2px;">سلاسة بصرية فائقة وموفرة للطاقة</div>'
                f'      </div>'
                f'    </div>'
                f'    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">'
                f'      <div style="font-size:13px;font-weight:800;color:#00E5FF;padding:5px 14px;background:rgba(0,229,255,0.12);'
                f'                  border:1px solid rgba(0,229,255,0.3);border-radius:20px;font-family:monospace;letter-spacing:1px;">ADAPTIVE SYNC</div>'
                f'      <div style="font-size:13px;color:rgba(255,255,255,0.45);font-weight:600;">استجابة لمسية لحظية</div>'
                f'    </div>'
                f'  </div>'
                f'</div>'
            )
        elif is_battery:
            visual_graphic_html = (
                f'<div style="margin-top:24px;padding:22px 28px;background:rgba(0,0,0,0.45);'
                f'            border:1.5px solid rgba(53,211,153,0.25);border-radius:24px;position:relative;'
                f'            box-shadow:inset 0 0 30px rgba(53,211,153,0.08);">'
                f'  <div style="display:flex;justify-content:space-between;align-items:center;gap:20px;">'
                f'    <div style="display:flex;align-items:center;gap:14px;">'
                f'      <div style="width:52px;height:52px;border-radius:14px;border:2px solid #35D399;'
                f'                  display:flex;align-items:center;justify-content:center;background:rgba(53,211,153,0.1);box-shadow:0 0 25px rgba(53,211,153,0.35);">'
                f'        <span style="font-size:22px;font-weight:900;color:#35D399;font-family:monospace;">PWR</span>'
                f'      </div>'
                f'      <div>'
                f'        <div style="font-size:20px;font-weight:900;color:#ffffff;">بطارية ضخمة وإدارة طاقة ذكية</div>'
                f'        <div style="font-size:14px;color:rgba(255,255,255,0.55);margin-top:2px;">عمر تشغيل ممتد وشحن فائق السرعة</div>'
                f'      </div>'
                f'    </div>'
                f'    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">'
                f'      <div style="font-size:13px;font-weight:800;color:#35D399;padding:5px 14px;background:rgba(53,211,153,0.12);'
                f'                  border:1px solid rgba(53,211,153,0.3);border-radius:20px;font-family:monospace;letter-spacing:1px;">FAST CHARGE</div>'
                f'      <div style="font-size:13px;color:rgba(255,255,255,0.45);font-weight:600;">كفاءة استهلاك طاقة عالية</div>'
                f'    </div>'
                f'  </div>'
                f'</div>'
            )
        else:
            visual_graphic_html = (
                f'<div style="margin-top:24px;padding:22px 28px;background:rgba(0,0,0,0.45);'
                f'            border:1.5px solid rgba(0,229,255,0.25);border-radius:24px;position:relative;'
                f'            box-shadow:inset 0 0 30px rgba(0,229,255,0.08);">'
                f'  <div style="display:flex;justify-content:space-between;align-items:center;gap:20px;">'
                f'    <div style="display:flex;align-items:center;gap:14px;">'
                f'      <div style="width:52px;height:52px;border-radius:14px;border:2px solid #00E5FF;'
                f'                  display:flex;align-items:center;justify-content:center;background:rgba(0,229,255,0.1);box-shadow:0 0 25px rgba(0,229,255,0.35);">'
                f'        <span style="font-size:20px;font-weight:900;color:#00E5FF;font-family:monospace;">SPEC</span>'
                f'      </div>'
                f'      <div>'
                f'        <div style="font-size:20px;font-weight:900;color:#ffffff;">مواصفات عتاد من الفئة الرائدة</div>'
                f'        <div style="font-size:14px;color:rgba(255,255,255,0.55);margin-top:2px;">معمارية متطورة وأداء استثنائي</div>'
                f'      </div>'
                f'    </div>'
                f'    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">'
                f'      <div style="font-size:13px;font-weight:800;color:#00E5FF;padding:5px 14px;background:rgba(0,229,255,0.12);'
                f'                  border:1px solid rgba(0,229,255,0.3);border-radius:20px;font-family:monospace;letter-spacing:1px;">FLAGSHIP GRADE</div>'
                f'      <div style="font-size:13px;color:rgba(255,255,255,0.45);font-weight:600;">سرعة واستقرار فائق</div>'
                f'    </div>'
                f'  </div>'
                f'</div>'
            )

    elif is_financial:
        # ── ABSOLUTE FINANCIAL VOLUME / NUMERICAL HISTOGRAM & APEX PEAK ──
        badge_text = "مؤشر مالي"
        badge_color = "#35D399"
        header_title = label_text or "حجم النمو المالي"

        col_heights = [30, 48, 66, 84, 104, 126]
        col_labels  = ['Q1', 'Q2', 'Q3', 'Q4', 'توسع', 'الذروة']
        fill_factor = min(1.0, max(0.0, (reveal - 0.2) / 0.5))

        cols_html = ""
        for i, h in enumerate(col_heights):
            is_last = (i == len(col_heights) - 1)
            anim_h  = round(h * fill_factor, 1)
            col_bg  = f'linear-gradient(180deg, #FFB700 0%, {slide_accent} 100%)' if is_last else 'linear-gradient(180deg, rgba(255,255,255,0.22) 0%, rgba(255,255,255,0.03) 100%)'
            col_sh  = f'box-shadow: 0 0 25px {slide_accent}, 0 0 10px #FFB700;' if is_last else 'border:1px solid rgba(255,255,255,0.08);'
            beacon  = f'<div style="position:absolute;top:-10px;left:50%;transform:translateX(-50%);width:18px;height:18px;border-radius:50%;background:#ffffff;box-shadow:0 0 14px #ffffff,0 0 25px {slide_accent};"></div>' if is_last else ''

            cols_html += (
                f'<div style="display:flex;flex-direction:column;align-items:center;gap:8px;flex:1;">'
                f'  <div style="width:100%;max-width:34px;height:130px;display:flex;align-items:flex-end;justify-content:center;position:relative;">'
                f'    {beacon}'
                f'    <div style="width:100%;height:{anim_h}px;border-radius:8px 8px 4px 4px;background:{col_bg};{col_sh}"></div>'
                f'  </div>'
                f'  <span style="font-size:15px;font-weight:{900 if is_last else 600};color:{slide_accent if is_last else "rgba(255,255,255,0.4)"};white-space:nowrap;">{col_labels[i]}</span>'
                f'</div>'
            )

        visual_graphic_html = (
            f'<div style="margin-top:24px;padding:20px 24px 14px;background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.07);border-radius:24px;">'
            f'  <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:12px;direction:rtl;">'
            f'    {cols_html}'
            f'  </div>'
            f'</div>'
        )

    else:
        # ── GENERAL NUMERICAL FACT & STAT CARD ──
        badge_text = "بيانات موثقة"
        badge_color = slide_accent
        header_title = label_text or "إحصائية موثقة"
        visual_graphic_html = (
            f'<div style="margin-top:22px;padding:16px 24px;background:rgba(255,255,255,0.04);'
            f'            border:1px solid rgba(255,255,255,0.1);border-radius:20px;display:flex;'
            f'            align-items:center;justify-content:space-between;">'
            f'  <span style="font-size:18px;font-weight:700;color:rgba(255,255,255,0.85);">{label_text or headline}</span>'
            f'  <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{slide_accent};box-shadow:0 0 14px {slide_accent};"></span>'
            f'</div>'
        )

    pulse_dot = f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{badge_color};box-shadow:0 0 10px {badge_color};margin-left:8px;"></span>'

    return (
        f'<div style="margin-top:40px;transform:translateY({d_y}px);opacity:{d_op};width:100%;max-width:880px;">'
        f'  <div style="background:linear-gradient(145deg,rgba(255,255,255,0.08) 0%,rgba(15,15,25,0.85) 100%);'
        f'              border:1.5px solid rgba(255,255,255,0.14);border-radius:36px;padding:32px 44px;'
        f'              box-shadow:0 25px 60px rgba(0,0,0,0.6), 0 0 60px {slide_accent}25;'
        f'              backdrop-filter:blur(25px);display:flex;flex-direction:column;">'
        f'    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
        f'      <span style="font-size:30px;font-weight:800;color:rgba(255,255,255,0.9);letter-spacing:-0.5px;">{header_title}</span>'
        f'      <span style="display:inline-flex;align-items:center;gap:8px;background:{badge_color}18;border:1.5px solid {badge_color}44;color:{badge_color};font-size:22px;padding:6px 18px;border-radius:50px;font-weight:800;">'
        f'        {pulse_dot} {badge_text}'
        f'      </span>'
        f'    </div>'
        f'    <div style="display:flex;align-items:baseline;gap:16px;margin:6px 0;">'
        f'      <span style="font-size:110px;font-weight:900;line-height:1;letter-spacing:-3px;'
        f'                   background:linear-gradient(135deg,#ffffff 40%,{slide_accent});'
        f'                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;'
        f'                   filter:drop-shadow(0 0 35px {slide_accent}88);">{num_str}</span>'
        f'    </div>'
        f'    {visual_graphic_html}'
        f'  </div>'
        f'</div>'
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
    is_ministry_ident = slide.get("is_ministry_ident", False)
    image_url = slide.get("image_url", "")
    brand_mode = slide.get("brand_mode")
    if not brand_mode:
        brand_mode = "ministry" if slide.get("show_ministry_logo", True) else "client"
    show_ministry_logo = (brand_mode == "ministry")
    ministry_logo = _get_ministry_logo_b64() if show_ministry_logo else ""

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
    # Cover always uses orange, outro uses purple, ministry ident uses luxury gold
    if is_ministry_ident:
        slide_accent, slide_accent_light, bg_tint = ("#FFB700", "#FFD700", "#140f03")
    elif is_cover:
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

    # ── DEDICATED MINISTRY EMBLEM IDENT SLIDE (Full Screen Center Stage) ──
    if is_ministry_ident:
        ident_logo = ministry_logo or _get_ministry_logo_b64()

        # Grand scale and bloom entrance
        ident_scale = round(0.80 + 0.22 * ent_ease, 3)
        aura_scale  = round(0.70 + 0.35 * ent_ease, 3)
        ident_glow  = round(0.25 + 0.50 * ent_ease, 2)

        ident_content = (
            '<div style="position:absolute;inset:0;display:flex;flex-direction:column;'
            'justify-content:center;align-items:center;padding:80px 60px;z-index:30;">'

            # Header National Pill
            '<div style="transform:translateY(' + str(h_y) + 'px) scale(' + str(h_scale) + ');opacity:' + str(h_op) + ';'
            'display:inline-flex;align-items:center;gap:14px;padding:12px 36px;border-radius:100px;'
            'background:rgba(212,175,55,0.12);border:1.5px solid rgba(212,175,55,0.45);'
            'box-shadow:0 0 35px rgba(212,175,55,0.25);margin-bottom:36px;">'
            '<svg width="28" height="20" viewBox="0 0 28 20" style="border-radius:3px;box-shadow:0 0 6px rgba(0,0,0,0.5);flex-shrink:0;">'
            '<rect width="28" height="6.67" y="0" fill="#00732f"/>'
            '<rect width="28" height="6.67" y="6.67" fill="#ffffff"/>'
            '<rect width="28" height="6.67" y="13.33" fill="#000000"/>'
            '<rect width="8" height="20" x="0" y="0" fill="#ff0000"/>'
            '</svg>'
            '<span style="font-size:24px;font-weight:900;color:#FFB700;letter-spacing:3px;">دولة الإمارات العربية المتحدة</span>'
            '</div>'

            # Ambient Pulsing Aura behind logo
            '<div style="position:absolute;width:960px;height:960px;border-radius:50%;'
            'background:radial-gradient(circle,rgba(212,175,55,' + str(ident_glow) + ') 0%,rgba(255,92,0,0.12) 40%,transparent 70%);'
            'transform:scale(' + str(aura_scale) + ');pointer-events:none;z-index:-1;"></div>'

            # Concentric Luxury Rings
            '<div style="position:absolute;width:820px;height:820px;border-radius:50%;'
            'border:2px solid rgba(212,175,55,0.22);box-shadow:0 0 50px rgba(212,175,55,0.15);'
            'transform:scale(' + str(h_scale) + ');pointer-events:none;z-index:-1;"></div>'
            '<div style="position:absolute;width:720px;height:720px;border-radius:50%;'
            'border:1.5px dashed rgba(212,175,55,0.35);'
            'transform:scale(' + str(h_scale) + ');pointer-events:none;z-index:-1;"></div>'

            # THE MAIN FULL EMBLEM CARD (Center of the screen)
            '<div style="transform:scale(' + str(ident_scale) + ');opacity:' + str(h_op) + ';'
            'background:rgba(255,255,255,0.97);backdrop-filter:blur(30px);-webkit-backdrop-filter:blur(30px);'
            'padding:40px 50px;border-radius:48px;'
            'box-shadow:0 30px 90px rgba(0,0,0,0.8), 0 0 85px rgba(212,175,55,0.5);'
            'border:3.5px solid rgba(212,175,55,0.65);display:flex;align-items:center;justify-content:center;'
            'max-width:780px;width:86%;min-height:640px;height:640px;box-sizing:border-box;">'
            '<img src="' + ident_logo + '" style="width:680px;max-width:92%;height:auto;max-height:480px;object-fit:contain;'
            'filter:drop-shadow(0 8px 24px rgba(0,0,0,0.22));" alt="وزارة تمكين المجتمع" />'
            '</div>'

            # Elegant Typography Subtitle below
            '<div style="transform:translateY(' + str(d_y) + 'px);opacity:' + str(d_op) + ';'
            'margin-top:36px;text-align:center;">'
            '<div style="font-size:38px;font-weight:900;color:#ffffff;letter-spacing:1.5px;'
            'text-shadow:0 4px 25px rgba(0,0,0,0.9);line-height:1.3;">'
            + (headline or "وزارة تمكين المجتمع") + '</div>'
            '<div style="font-size:19px;font-weight:700;color:rgba(255,183,0,0.9);letter-spacing:3px;'
            'margin-top:10px;direction:ltr;">' + (detail or "MINISTRY OF COMMUNITY EMPOWERMENT") + '</div>'
            '<div style="width:160px;height:4px;margin:24px auto 0;'
            'background:linear-gradient(90deg,transparent,#FFB700,#FF5C00,transparent);border-radius:2px;"></div>'
            '</div>'

            '</div>'
        )

        return (
            "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>"
            + cairo_css + css_base + "</style></head><body>"
            + bg_layers + top_bar + dot_bar + ident_content
            # Footer
            + '<div style="position:absolute;bottom:70px;left:0;right:0;text-align:center;">'
            '<span style="font-size:22px;color:rgba(255,255,255,0.35);letter-spacing:3px;font-weight:600;">'
            'محتوى رسمي معتمد · دولة الإمارات العربية المتحدة</span></div>'
            + "</body></html>"
        )

    # ── OUTRO ─────────────────────────────────────────────────────────────
    elif is_outro:
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
        cover_footer_text = "وزارة تمكين المجتمع" if brand_mode == "ministry" else (author_name + " · @" + brand)
        return (
            "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>"
            + cairo_css + css_base + "</style></head><body>"
            + bg_layers + top_bar + dot_bar + content
            # Footer brand
            + '<div style="position:absolute;bottom:80px;left:80px;right:80px;text-align:center;">'
            '<span style="font-size:24px;color:rgba(255,255,255,0.4);letter-spacing:3px;font-weight:700;">'
            + cover_footer_text + '</span></div>'
            + "</body></html>"
        )

    # ── CTA SLIDE ─────────────────────────────────────────────────────────
    elif is_cta:
        if brand_mode == "ministry":
            # Ministry CTA Slide — Official Institutional Branding
            m_logo = ministry_logo or _get_ministry_logo_b64()
            logo_html = ""
            if m_logo:
                logo_html = (
                    '<div style="background:rgba(255,255,255,0.97);padding:40px 50px;border-radius:48px;'
                    'box-shadow:0 0 90px rgba(212,175,55,0.5), 0 30px 90px rgba(0,0,0,0.75);'
                    'border:3.5px solid rgba(212,175,55,0.65);'
                    'transform:scale(' + str(h_scale) + ');opacity:' + str(h_op) + ';margin-bottom:24px;'
                    'max-width:780px;width:86%;min-height:660px;height:660px;box-sizing:border-box;'
                    'display:flex;align-items:center;justify-content:center;">'
                    '<img src="' + m_logo + '" style="width:680px;max-width:92%;height:auto;max-height:480px;object-fit:contain;'
                    'filter:drop-shadow(0 8px 24px rgba(0,0,0,0.2));" alt="وزارة تمكين المجتمع" />'
                    '</div>'
                )

            category_pill = (
                '<div style="margin-bottom:22px;transform:translateY(' + str(h_y) + 'px);opacity:' + str(h_op) + ';">'
                '<div style="display:inline-block;padding:10px 36px;border-radius:30px;'
                'background:rgba(212,175,55,0.18);border:1.5px solid #FFB700;">'
                '<span style="font-size:26px;font-weight:800;color:#FFB700;">' + (category or "شاركونا رأيكم") + '</span>'
                '</div></div>'
            )

            headline_html = (
                '<div style="transform:translateY(' + str(h_y) + 'px);opacity:' + str(h_op) + ';text-align:center;max-width:920px;margin-bottom:20px;">'
                '<div style="font-size:52px;font-weight:900;color:#fff;line-height:1.3;letter-spacing:-1px;'
                'text-shadow:0 4px 30px rgba(0,0,0,0.5);">'
                + headline[:130] + '</div>'
                '</div>'
            )

            detail_text = detail or "اكتبوا آراءكم ومقترحاتكم في التعليقات"
            detail_html = (
                '<div style="padding:12px 32px;border-radius:12px;'
                'background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);'
                'transform:translateY(' + str(d_y) + 'px);opacity:' + str(d_op) + ';">'
                '<span style="font-size:26px;font-weight:600;color:rgba(255,255,255,0.8);">'
                + detail_text + '</span></div>'
            )

            content = (
                '<div style="position:absolute;inset:0;display:flex;flex-direction:column;'
                'justify-content:center;align-items:center;padding:50px 80px 80px;">'
                + logo_html
                + category_pill
                + headline_html
                + detail_html
                + '</div>'
            )
            return (
                "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>"
                + cairo_css + css_base + "</style></head><body>"
                + bg_layers + top_bar + dot_bar + content
                + '<div style="position:absolute;bottom:70px;left:0;right:0;text-align:center;">'
                '<span style="font-size:22px;color:rgba(255,255,255,0.4);letter-spacing:2px;font-weight:600;">'
                'وزارة تمكين المجتمع · دولة الإمارات العربية المتحدة</span></div>'
                + "</body></html>"
            )

        else:
            # Client (Dr. Zayed) CTA Slide with avatar and personal branding
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

            detail_text = detail or "اكتب رأيك في التعليقات"
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
                + '<div style="position:absolute;bottom:70px;left:80px;right:80px;display:flex;justify-content:center;">'
                '<span style="font-size:22px;color:rgba(255,255,255,0.4);letter-spacing:2px;font-weight:600;">'
                + author_name + ' · @' + brand + '</span></div>'
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

    visual_type = (slide.get("visual_type") or "").strip().upper()

    # Determine whether an epic HUD is displayed
    import re as _re
    has_num_in_detail = bool(detail and _re.search(r'\d', detail))
    
    if visual_type == "TEXT_ONLY":
        will_show_hud = False
    elif visual_type in ("PERCENTAGE_BAR", "FINANCIAL_METRIC", "TECH_SPEC"):
        will_show_hud = True
    elif visual_type == "COMPARISON" and len(bars) > 1:
        will_show_hud = True
    elif visual_type == "HIGHLIGHT_BADGE":
        will_show_hud = False
    else:
        will_show_hud = has_num_in_detail or len(bars) >= 1

    if will_show_hud:
        fs = min(fs, 76)

    # ── AI Visual Director & Unified Epic Data HUD ────────────────────────────
    hud_html = ""
    if visual_type == "TEXT_ONLY":
        # Pure cinematic text slide. If detail exists, show it as a clean subtle subtitle
        if detail and not (is_cover or is_cta or is_outro or is_ministry_ident):
            hud_html = (
                '<div style="margin-top:36px;transform:translateY(' + str(d_y) + 'px);opacity:' + str(d_op) + ';text-align:center;">'
                '<span style="font-size:32px;font-weight:600;color:rgba(255,255,255,0.75);letter-spacing:0.5px;">' + detail + '</span>'
                '</div>'
            )
        else:
            hud_html = ""
    elif visual_type == "TECH_SPEC":
        stat_text = detail or (bars[0].get("label", "") + " " + str(bars[0].get("value", ""))) if bars else headline
        pct_val = bars[0].get("pct") if bars else None
        hud_html = _render_hero_stat_hud(stat_text, pct_val, slide_accent, slide_accent_light, reveal, d_y, d_op, headline, force_type="TECH_SPEC")
    elif visual_type == "PERCENTAGE_BAR":
        stat_text = detail or (bars[0].get("label", "") + " " + str(bars[0].get("value", ""))) if bars else headline
        pct_val = bars[0].get("pct") if bars else None
        hud_html = _render_hero_stat_hud(stat_text, pct_val, slide_accent, slide_accent_light, reveal, d_y, d_op, headline, force_type="PERCENTAGE_BAR")
    elif visual_type == "FINANCIAL_METRIC":
        stat_text = detail or (bars[0].get("label", "") + " " + str(bars[0].get("value", ""))) if bars else headline
        pct_val = bars[0].get("pct") if bars else None
        hud_html = _render_hero_stat_hud(stat_text, pct_val, slide_accent, slide_accent_light, reveal, d_y, d_op, headline, force_type="FINANCIAL_METRIC")
    elif visual_type == "COMPARISON" and len(bars) > 1:
        hud_html = _render_multi_bar_dashboard(bars, slide_accent, reveal, d_y, d_op)
    elif visual_type == "HIGHLIGHT_BADGE":
        badge_content = detail or headline
        hud_html = (
            '<div style="margin-top:44px;transform:translateY(' + str(d_y) + 'px);opacity:' + str(d_op) + ';text-align:center;">'
            '<div style="padding:16px 42px;border-radius:24px;background:rgba(255,255,255,0.07);'
            'border:1.5px solid ' + slide_accent + '44;display:inline-block;box-shadow:0 12px 36px rgba(0,0,0,0.4), 0 0 30px ' + slide_accent + '22;">'
            '<span style="font-size:32px;font-weight:700;color:rgba(255,255,255,0.95);line-height:1.4;">' + badge_content + '</span>'
            '</div></div>'
        )
    else:
        # Fallback to smart heuristic if visual_type not explicitly given
        if len(bars) > 1:
            hud_html = _render_multi_bar_dashboard(bars, slide_accent, reveal, d_y, d_op)
        elif will_show_hud:
            stat_text = detail or (bars[0].get("label", "") + " " + str(bars[0].get("value", "")))
            pct_val = bars[0].get("pct") if bars else None
            hud_html = _render_hero_stat_hud(stat_text, pct_val, slide_accent, slide_accent_light, reveal, d_y, d_op, headline)
        elif detail:
            hud_html = (
                '<div style="margin-top:44px;transform:translateY(' + str(d_y) + 'px);opacity:' + str(d_op) + ';text-align:center;">'
                '<div style="padding:14px 36px;border-radius:16px;background:rgba(255,255,255,0.06);'
                'border:1.5px solid rgba(255,255,255,0.12);display:inline-block;box-shadow:0 10px 30px rgba(0,0,0,0.3);">'
                '<span style="font-size:30px;font-weight:600;color:rgba(255,255,255,0.85);line-height:1.4;">' + detail + '</span>'
                '</div></div>'
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

    # Slide number — small accent watermark label (synchronized with slide number)
    num_label = ""
    display_num = slide.get("number") or (label.zfill(2) if label else "")
    if display_num and not (is_cover or is_cta or is_outro or is_ministry_ident):
        num_label = (
            '<div style="margin-bottom:20px;opacity:0.5;">'
            '<span style="font-size:120px;font-weight:900;color:' + slide_accent + '15;'
            'position:absolute;right:80px;top:50%;transform:translateY(-80%);pointer-events:none;">'
            + str(display_num).zfill(2) + '</span></div>'
        )

    # Accent vertical line decoration
    accent_line = (
        '<div style="position:absolute;right:65px;top:50%;transform:translateY(-50%);'
        'width:4px;height:200px;border-radius:2px;'
        'background:linear-gradient(to bottom,transparent,' + slide_accent + ',' + slide_accent_light + ',transparent);'
        'opacity:0.4;"></div>'
    )

    normal_footer_text = "وزارة تمكين المجتمع · دولة الإمارات العربية المتحدة" if brand_mode == "ministry" else (author_name + " · @" + brand)

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
        # Data HUD / Note below
        + '<div style="width:100%;display:flex;justify-content:center;">'
        + hud_html
        + '</div>'
        + '</div>'
        # Footer
        + '<div style="position:absolute;bottom:70px;left:80px;right:80px;'
        'display:flex;justify-content:center;">'
        '<span style="font-size:22px;color:rgba(255,255,255,0.4);letter-spacing:2px;font-weight:600;">'
        + normal_footer_text + '</span></div>'
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
    content_idx = 0
    for idx, slide in enumerate(slides_data):
        slide["total"]   = total
        slide["current"] = idx + 1
        if slide.get("is_ministry_ident"):
            slide["number"] = ""
            slide["label"] = ""
        else:
            content_idx += 1
            num_str = str(content_idx).zfill(2)
            slide["number"] = num_str
            slide["label"]  = num_str

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

    # Save metadata sidecar
    try:
        import json as _json
        b_mode = slides_data[0].get("brand_mode", "ministry") if slides_data else "ministry"
        meta_file = OUTPUT_DIR / (out_filename + ".json")
        with open(meta_file, "w", encoding="utf-8") as mf:
            _json.dump({
                "content_item_id": content_item_id,
                "brand_mode": b_mode,
                "url": "/static/video_output/" + out_filename,
                "timestamp": timestamp,
            }, mf)
    except Exception:
        pass

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
    brand_mode: str = "ministry",
) -> List[Dict[str, Any]]:
    slides: List[Dict[str, Any]] = []

    def base(extra: dict) -> dict:
        return {
            "brand": brand,
            "author_name": author_name,
            "article_title": article_title,
            "bars": [],
            "brand_mode": brand_mode,
            "show_ministry_logo": (brand_mode == "ministry"),
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
                "detail": "اكتب رأيك في التعليقات",
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
                    "detail": body[:80] or detail[:80] or "اكتب رأيك في التعليقات",
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
        raw_slides = generated_content.get("slides", []) if isinstance(generated_content, dict) else []

        # ── Opening Ministry Ident Slide (Only for Ministry brand mode) ───
        if brand_mode == "ministry":
            opening_ident = base({
                "is_ministry_ident": True,
                "is_cover": False,
                "category": "دولة الإمارات العربية المتحدة",
                "headline": "وزارة تمكين المجتمع",
                "detail": "MINISTRY OF COMMUNITY EMPOWERMENT",
                "label": "",
                "visual_type": "TEXT_ONLY",
                "show_ministry_logo": True,
            })
            slides.append(opening_ident)

        for i, s in enumerate(raw_slides):
            if isinstance(s, dict):
                text = s.get("text") or s.get("heading") or s.get("title") or ""
                note = s.get("note") or s.get("body") or s.get("detail") or ""
                visual_type = (s.get("visual_type") or "").strip().upper()
            elif isinstance(s, str):
                text = s
                note = ""
                visual_type = ""
            else:
                text = str(s or "")
                note = ""
                visual_type = ""
            is_first = (i == 0)
            is_last  = (i == len(raw_slides) - 1)

            # Enforce clean text for first (Hook) and last (CTA) slides if unspecified
            if is_first or is_last:
                visual_type = visual_type or "TEXT_ONLY"

            slides.append(base({
                "is_cover": is_first,
                "is_cta": is_last,
                "category": "ابدأ" if is_first else ("شاركنا رأيك" if is_last else ""),
                "label": "",
                "headline": str(text)[:150],
                "detail": str(note)[:80] if note else "",
                "visual_type": visual_type,
                "bars": _extract_bars_from_text(str(text) + " " + str(note)) if (note and not is_last) else [],
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
