"""
Carousel Image Renderer — @ak4app Professional Edition
Format: 1080×1350 (4:5 portrait)
Matches the exact aesthetic requested by the user from provided screenshots:
Supports 2 distinct random styles:
1. Dark Flat (The initial sleek dark theme with solid/outline columns)
2. Light Card (The new white rounded card on a gray background with colored blobs)
"""

import asyncio
import random
from pathlib import Path
from typing import List, Dict, Any
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent.parent.parent / "static" / "carousel_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_URL = "https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap"

THEMES = [
    {"id": "violet",   "bg": "#121629", "accent": "#a855f7", "accent_light": "#f472b6"},
    {"id": "blue",     "bg": "#0f172a", "accent": "#3b82f6", "accent_light": "#38bdf8"},
    {"id": "teal",     "bg": "#112e33", "accent": "#14b8a6", "accent_light": "#5eead4"},
    {"id": "rose",     "bg": "#2e0f15", "accent": "#f43f5e", "accent_light": "#fda4af"},
    {"id": "brown",    "bg": "#3c3329", "accent": "#c19b6c", "accent_light": "#e2c8a3"}, # Matches Image 1 precisely
]

# ─── STYLE 1: DARK FLAT ────────────────────────────────────────────────────────

def _progress_dark(current: int, total: int, accent: str) -> str:
    segs = []
    for i in range(total):
        color = accent if i <= current else "rgba(255,255,255,0.15)"
        segs.append(f'<div style="flex:1;height:4px;border-radius:2px;background:{color};"></div>')
    return f'<div style="display:flex;gap:10px;padding:30px 40px 10px;">{"".join(segs)}</div>'

def _header_dark(current: int, total: int) -> str:
    return f"""
    <div style="padding: 10px 40px 0; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <span style="color: rgba(255,255,255,0.5); font-size: 22px; font-weight: 700;">{total}/{current+1}</span>
    </div>
    """

def _slide_wrapper_dark(t: dict, progress_html: str, header_html: str, main_html: str, brand: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<link href="{FONT_URL}" rel="stylesheet">
<style>
  * {{ margin:0;padding:0;box-sizing:border-box; font-family:'Cairo',sans-serif; }}
  html, body {{ width:1080px;height:1350px; overflow:hidden; }}
  body {{ background:{t['bg']}; color:#fff; display:flex;flex-direction:column; }}
</style>
</head>
<body>
  {progress_html}
  {header_html}
  {main_html}
  <div style="padding: 40px; margin-top: auto;">
    <span style="font-size:24px;color:rgba(255,255,255,0.5);font-weight:600;">@{brand}</span>
  </div>
</body>
</html>"""

def render_quote_slide_dark(t: dict, slide: dict, idx: int, total: int, brand: str) -> str:
    heading, body = slide.get("heading", ""), slide.get("body", "")
    text = f"{heading}: {body}" if heading and body else (heading or body)
    main = f"""
    <div style="flex:1; display:flex; flex-direction:column; justify-content:center; padding: 0 50px;">
        <div style="background:{t['accent']}; border-radius: 24px; padding: 100px 50px 50px; position:relative; text-align:center;">
            <div style="position:absolute; top: -10px; right: 40px; font-size: 180px; color: rgba(255,255,255,0.2); font-family: sans-serif; line-height:1; font-weight:900;">"</div>
            <h2 style="color:#fff; font-size: 55px; font-weight: 900; line-height: 1.4; margin-bottom: 60px; position:relative; z-index:2;">{text}</h2>
            <div style="color: rgba(255,255,255,0.7); font-size: 30px; font-weight: 700;">ملاحظة</div>
        </div>
    </div>
    """
    return _slide_wrapper_dark(t, _progress_dark(idx, total, t['accent']), _header_dark(idx, total), main, brand)

def render_two_col_slide_dark(t: dict, slide: dict, idx: int, total: int, brand: str) -> str:
    heading, lt, li, rt, ri = slide.get("heading", ""), slide.get("left_column_title", ""), slide.get("left_column_items") or [], slide.get("right_column_title", ""), slide.get("right_column_items") or []
    def col_items(items): return "".join(f'<div style="margin-bottom: 30px;">{item}</div>' for item in items)
    main = f"""
    <div style="flex:1; display:flex; flex-direction:column; justify-content:center; padding: 0 50px;">
        <h2 style="text-align:center; color:{t['accent']}; font-size: 60px; font-weight: 900; margin-bottom: 60px;">{heading}</h2>
        <div style="display:flex; gap: 30px;">
            <div style="flex:1; background:{t['accent']}; border-radius: 20px; padding: 50px 20px; text-align:center;">
                <h3 style="color:#fff; font-size:45px; font-weight:900; margin-bottom:50px;">{lt}</h3>
                <div style="color:#fff; font-size:36px; font-weight:700; line-height:1.4;">{col_items(li)}</div>
            </div>
            <div style="flex:1; background:transparent; border: 3px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 50px 20px; text-align:center;">
                <h3 style="color:{t['accent_light']}; font-size:45px; font-weight:900; margin-bottom:50px;">{rt}</h3>
                <div style="color:#fff; font-size:36px; font-weight:700; line-height:1.4;">{col_items(ri)}</div>
            </div>
        </div>
    </div>
    """
    return _slide_wrapper_dark(t, _progress_dark(idx, total, t['accent']), _header_dark(idx, total), main, brand)

def render_tips_slide_dark(t: dict, slide: dict, idx: int, total: int, brand: str) -> str:
    heading, body, tips = slide.get("heading", ""), slide.get("body", ""), slide.get("tips_list") or []
    if body and not tips: tips = [body]
    icons = ["✓", "📊", "⚡", "💡", "🎯", "🔥"]
    tips_html = "".join(f'<div style="display:flex; align-items:center; gap: 30px; margin-bottom: 45px;"><div style="width: 55px; height: 55px; border-radius: 50%; background: {t["accent"]}33; display:flex; align-items:center; justify-content:center; flex-shrink:0;"><span style="color:{t["accent_light"]}; font-size: 26px;">{icons[i % len(icons)]}</span></div><div style="font-size: 38px; font-weight: 700; color: #fff; line-height: 1.4;">{tip}</div></div>' for i, tip in enumerate(tips))
    main = f'<div style="flex:1; display:flex; flex-direction:column; justify-content:center; padding: 0 60px;"><h2 style="color:{t["accent"]}; font-size: 60px; font-weight: 900; margin-bottom: 70px; line-height:1.3;">{heading}</h2><div>{tips_html}</div></div>'
    return _slide_wrapper_dark(t, _progress_dark(idx, total, t['accent']), _header_dark(idx, total), main, brand)


# ─── STYLE 2: LIGHT CARD ───────────────────────────────────────────────────────

def render_light_card_slide(t: dict, slide: dict, idx: int, total: int, brand: str) -> str:
    heading = slide.get("heading", "")
    body = slide.get("body", "")
    tips = slide.get("tips_list") or []
    is_two_col = slide.get("left_column_title") is not None
    
    blob_color = t['bg']
    accent_color = t['accent']
    text_color = t['bg']
    
    watermark = f"""
    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); opacity:0.07; z-index:0; pointer-events:none;">
        <svg width="600" height="600" viewBox="0 0 100 100" fill="none" stroke="{accent_color}" stroke-width="2">
            <circle cx="50" cy="50" r="30"/>
            <ellipse cx="50" cy="50" rx="45" ry="15" transform="rotate(45 50 50)"/>
            <ellipse cx="50" cy="50" rx="45" ry="15" transform="rotate(-45 50 50)"/>
        </svg>
    </div>
    """

    content_html = ""
    if is_two_col:
        lt, li = slide.get("left_column_title", ""), slide.get("left_column_items") or []
        rt, ri = slide.get("right_column_title", ""), slide.get("right_column_items") or []
        col_items = lambda items: "".join(f'<div style="margin-bottom:15px;">{item}</div>' for item in items)
        content_html = f'<h2 style="color:{text_color}; font-size:60px; font-weight:900; line-height:1.4; margin-bottom:50px; position:relative; z-index:1;">{heading}</h2>'
        content_html += f"""
        <div style="display:flex; gap:20px; position:relative; z-index:1; width:100%;">
            <div style="flex:1; background:{blob_color}; padding: 40px 20px; border-radius:20px;">
                <h3 style="color:#fff; font-size:40px; font-weight:900; margin-bottom:30px;">{lt}</h3>
                <div style="color:#fff; font-size:32px; font-weight:700; line-height:1.4;">{col_items(li)}</div>
            </div>
            <div style="flex:1; background:rgba(0,0,0,0.04); padding: 40px 20px; border-radius:20px;">
                <h3 style="color:{text_color}; font-size:40px; font-weight:900; margin-bottom:30px;">{rt}</h3>
                <div style="color:{text_color}; font-size:32px; font-weight:700; line-height:1.4;">{col_items(ri)}</div>
            </div>
        </div>
        """
    elif heading and not tips and not body:
        # Quote style
        content_html = f'<h2 style="color:{text_color}; font-size:75px; font-weight:900; line-height:1.4; position:relative; z-index:1;">{heading}</h2>'
    elif heading and body and not tips:
        content_html = f'<h2 style="color:{text_color}; font-size:70px; font-weight:900; line-height:1.4; margin-bottom:40px; position:relative; z-index:1;">{heading}</h2>'
        content_html += f'<p style="color:{text_color}; font-size:45px; font-weight:700; line-height:1.4; position:relative; z-index:1;">{body}</p>'
    elif tips:
        content_html = f'<h2 style="color:{text_color}; font-size:55px; font-weight:900; line-height:1.4; margin-bottom:30px; position:relative; z-index:1;">{heading}</h2>'
        tips_list = "".join(f'<div style="color:{accent_color}; font-size:40px; font-weight:900; margin-bottom:15px; display:flex; gap:15px; text-align:right;"><span style="flex-shrink:0;">•</span> <span style="color:{text_color}; font-size:38px; line-height:1.4;">{tip}</span></div>' for tip in tips)
        content_html += f'<div style="position:relative; z-index:1;">{tips_list}</div>'
        if body: content_html += f'<p style="color:{text_color}; font-size:35px; font-weight:900; line-height:1.4; margin-top:30px; position:relative; z-index:1;">{body}</p>'

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<link href="{FONT_URL}" rel="stylesheet">
<style>
  * {{ margin:0;padding:0;box-sizing:border-box; font-family:'Cairo',sans-serif; }}
  html, body {{ width:1080px; height:1350px; overflow:hidden; }}
  body {{ background:#f3f4f6; display:flex; align-items:center; justify-content:center; position:relative; }}
</style>
</head>
<body>
    <div style="position:absolute; top:-100px; right:-100px; width:450px; height:450px; background:{blob_color}; border-radius:150px; transform:rotate(15deg);"></div>
    <div style="position:absolute; bottom:-100px; right:-50px; width:500px; height:350px; background:{blob_color}; border-radius:150px; transform:rotate(-10deg);"></div>
    <div style="position:absolute; top:50%; left:0; transform:translateY(-50%); width:0; height:0; border-top:60px solid transparent; border-bottom:60px solid transparent; border-left:80px solid {accent_color};"></div>
    <div style="position:absolute; top: 70px; right: 70px; color: #fff; font-size: 30px; font-weight: 700; z-index:20;">{total}/{idx+1}</div>
    <div style="width: 900px; height: 1150px; background:#ffffff; border-radius:60px; box-shadow:0 30px 60px rgba(0,0,0,0.08); display:flex; flex-direction:column; padding:80px 60px 50px; position:relative; z-index:10;">
        {watermark}
        <div style="flex:1; display:flex; flex-direction:column; justify-content:center; text-align:center;">{content_html}</div>
        <div style="text-align:center; position:relative; z-index:1;">
            <div style="color:{accent_color}; font-size:60px; font-weight:900; line-height:0.5; margin-bottom: 20px;">..</div>
            <div style="width:100%; height:2px; background:rgba(0,0,0,0.1); margin: 30px 0;"></div>
            <div style="color:{text_color}; font-size:24px; font-weight:700;">@{brand}</div>
        </div>
    </div>
</body>
</html>"""

# ─── CTA SLIDE (LAST SLIDE) ───────────────────────────────────────────────────

def render_cta_slide(t: dict, slide: dict, idx: int, total: int, brand: str) -> str:
    heading = slide.get("heading", "")
    body = slide.get("body", "")
    
    blob_color = t['bg']
    accent_color = t['accent']
    # If the theme is dark, the text should be light, and vice-versa
    text_color = t.get('text', '#ffffff' if t['id'] != 'light' else '#111827')
    
    import os
    import base64
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    image_path = os.path.join(base_dir, "static", "assets", "author_mic.jpg")
    
    img_src = ""
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                img_b64 = base64.b64encode(img_file.read()).decode('utf-8')
                img_src = f"data:image/jpeg;base64,{img_b64}"
    except Exception as e:
        print(f"Error loading CTA image: {e}")

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<link href="{FONT_URL}" rel="stylesheet">
<style>
  * {{ margin:0;padding:0;box-sizing:border-box; font-family:'Cairo',sans-serif; }}
  html, body {{ width:1080px; height:1350px; overflow:hidden; }}
  body {{ background:{blob_color}; display:flex; flex-direction:column; align-items:center; justify-content:center; position:relative; }}
  
  /* Decorative background elements */
  .bg-blob-1 {{ position:absolute; top:-150px; right:-150px; width:600px; height:600px; background:rgba(255,255,255,0.03); border-radius:50%; }}
  .bg-blob-2 {{ position:absolute; bottom:-100px; left:-100px; width:500px; height:500px; background:rgba(255,255,255,0.02); border-radius:50%; }}
  
  .content-container {{ width: 100%; z-index: 10; display:flex; flex-direction:column; align-items:center; justify-content:center; padding: 60px; text-align:center; }}
  
  .avatar-box {{
      width: 450px; height: 450px; border-radius: 50%;
      border: 15px solid rgba(255,255,255,0.05);
      box-shadow: 0 40px 80px rgba(0,0,0,0.2), inset 0 0 0 5px rgba(255,255,255,0.1);
      overflow: hidden; margin-bottom: 60px;
      background: #2c2c2c;
      position: relative;
  }}
  .avatar-box img {{ width:100%; height:100%; object-fit:cover; object-position: 35% 10%; }}
  
  .btn-follow {{ background:{accent_color}; color:#fff; font-size:55px; font-weight:900; padding:25px 70px; border-radius:70px; display:inline-flex; align-items:center; gap:20px; box-shadow:0 25px 50px rgba(0,0,0,0.3); margin-top:70px; border: 4px solid rgba(255,255,255,0.1); }}
</style>
</head>
<body>
    <div class="bg-blob-1"></div>
    <div class="bg-blob-2"></div>
    
    <div style="position:absolute; top: 70px; right: 70px; color: {text_color}; opacity: 0.5; font-size: 30px; font-weight: 700; z-index:20; background:rgba(0,0,0,0.2); padding:5px 20px; border-radius:20px;">{total}/{idx+1}</div>
    
    <div class="content-container">
        <div class="avatar-box">
            <img src="{img_src}" onerror="this.style.display='none'" alt="Author" />
        </div>

        <h2 style="color:{text_color}; font-size:75px; font-weight:900; line-height:1.4; margin-bottom:30px; text-shadow: 0 5px 15px rgba(0,0,0,0.1);">{heading}</h2>
        <p style="color:{text_color}; opacity:0.85; font-size:45px; font-weight:700; line-height:1.5; max-width: 900px;">{body}</p>
        
        <div class="btn-follow">
            <span>+ تابع </span>
            <span dir="ltr">@{brand}</span>
        </div>
    </div>
</body>
</html>"""

# ─── MAIN RENDERER ────────────────────────────────────────────────────────────

def render_custom_pdf_slide(template, slide: dict, i: int, total: int, brand: str, custom_text_color: str = None, custom_accent_color: str = None) -> str:
    # template is a SQLAlchemy CarouselTemplate object
    heading = slide.get("heading", "")
    body = slide.get("body", "")
    
    # Determine the background image to use
    if i == 0:
        bg_path = template.cover_bg_path
    elif i == total - 1:
        bg_path = template.cta_bg_path
    else:
        bg_path = template.body_bg_path
        
    if bg_path and bg_path.startswith("http"):
        bg_url = bg_path
    else:
        bg_url = f"http://127.0.0.1:8001{bg_path}"
        
    text_color = custom_text_color if custom_text_color else getattr(template, "text_color", "#ffffff")
    accent_color = custom_accent_color if custom_accent_color else getattr(template, "accent_color", "#3b82f6")
    style_mode = getattr(template, "style_mode", "glass_mixed")
    
    # Determine if text is dark or light to pick the right glass color
    is_text_dark = False
    try:
        hex_c = text_color.lstrip('#')
        if len(hex_c) == 6:
            r, g, b = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
            luminance = (0.299*r + 0.587*g + 0.114*b) / 255
            is_text_dark = luminance < 0.5
    except:
        pass
        
    if is_text_dark:
        glass_bg = "linear-gradient(145deg, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0.3) 100%)"
        glass_shadow = "0 20px 40px rgba(0,0,0,0.05), inset 0 2px 20px rgba(255,255,255,0.8)"
        side_bg = "linear-gradient(270deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0) 100%)"
    else:
        glass_bg = "linear-gradient(145deg, rgba(0,0,0,0.4) 0%, rgba(0,0,0,0.15) 100%)"
        glass_shadow = "0 30px 60px rgba(0,0,0,0.4), inset 0 2px 20px rgba(255,255,255,0.1)"
        side_bg = "linear-gradient(270deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0) 100%)"
    
    # For custom templates, we assume the user just wants the text placed nicely on the background
    
    avatar_html = ""
    container_class = "transparent-card"
    if style_mode == "glass_all":
        container_class = "glass-card"
    elif style_mode == "glass_mixed":
        if i == 0 or i == total - 1:
            container_class = "transparent-card"
        elif i % 2 != 0:
            container_class = "glass-card"
        else:
            container_class = "side-accent-card"
    
    if i == total - 1:
        import os
        import base64
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        image_path = os.path.join(base_dir, "static", "assets", "author_mic.jpg")
        img_src = ""
        try:
            if os.path.exists(image_path):
                with open(image_path, "rb") as img_file:
                    img_b64 = base64.b64encode(img_file.read()).decode('utf-8')
                    img_src = f"data:image/jpeg;base64,{img_b64}"
        except Exception:
            pass
            
        if img_src:
            avatar_html = f"""
            <div style="
                width: 400px; height: 400px; border-radius: 50%;
                border: 12px solid {accent_color};
                box-shadow: 0 30px 60px rgba(0,0,0,0.3);
                overflow: hidden; margin: 50px 0;
                background: #2c2c2c;
                flex-shrink: 0;
            ">
                <img src="{img_src}" style="width:100%; height:100%; object-fit:cover; object-position: 35% 10%;" />
            </div>
            """

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<link href="{FONT_URL}" rel="stylesheet">
<style>
  * {{ margin:0;padding:0;box-sizing:border-box; font-family:'Cairo',sans-serif; }}
  html, body {{ width:1080px; height:1350px; overflow:hidden; }}
  body {{ 
      background-image: url('{bg_url}'); 
      background-size: cover; 
      background-position: center;
      display:flex; flex-direction:column;
      justify-content: center;
      align-items: center;
      padding: 60px;
  }}
  .glass-card {{
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
      background: {glass_bg};
      backdrop-filter: blur(40px);
      border-radius: 50px;
      padding: 70px 90px;
      width: 85%;
      border: 1px solid rgba(255,255,255,0.2);
      border-top: 6px solid {accent_color};
      box-shadow: {glass_shadow};
  }}
  .transparent-card {{
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
      padding: 40px;
      width: 85%;
  }}
  .side-accent-card {{
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: flex-start;
      text-align: right;
      padding: 60px 80px 60px 40px;
      border-right: 12px solid {accent_color};
      background: {side_bg};
      border-radius: 0 40px 40px 0;
      width: 90%;
      align-self: flex-start;
  }}
  h2 {{ color: {accent_color}; font-size: 65px; font-weight: 900; margin-bottom: 40px; text-shadow: 0 4px 15px rgba(0,0,0,0.3); line-height: 1.4; }}
  p {{ color: {text_color}; font-size: 42px; font-weight: 700; line-height: 1.6; text-shadow: 0 2px 10px rgba(0,0,0,0.3); }}
</style>
</head>
<body>
    <div class="{container_class}">
        <h2>{heading}</h2>
        {avatar_html}
        <p>{body}</p>
    </div>
</body>
</html>"""
    return html

async def render_carousel_images(
    content_id: int,
    carousel_data: Dict[str, Any],
    brand_name: str = "zayedtech",
    template_id: int = None,
    custom_text_color: str = None,
    custom_accent_color: str = None
) -> List[str]:
    slides = carousel_data.get("slides", [])
    total = len(slides)
    if total == 0:
        return []

    theme = random.choice(THEMES)
    style = random.choice(["dark_flat", "light_card"])
    if theme["id"] == "brown":
        style = "light_card"

    # Fetch custom template if provided
    custom_template = None
    if template_id:
        from app.db.session import SessionLocal
        from app.models.carousel_template import CarouselTemplate
        db = SessionLocal()
        custom_template = db.query(CarouselTemplate).filter(CarouselTemplate.id == template_id).first()
        db.close()

    output_paths = []
    slide_dir = OUTPUT_DIR / str(content_id)
    slide_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})

        for i, slide in enumerate(slides):
            if custom_template:
                html = render_custom_pdf_slide(custom_template, slide, i, total, brand_name, custom_text_color, custom_accent_color)
            elif i == total - 1:
                html = render_cta_slide(theme, slide, i, total, brand_name)
            elif style == "light_card":
                html = render_light_card_slide(theme, slide, i, total, brand_name)
            else:
                has_two_col = slide.get("left_column_title") is not None
                if i == 0:
                    html = render_quote_slide_dark(theme, slide, i, total, brand_name)
                elif has_two_col:
                    html = render_two_col_slide_dark(theme, slide, i, total, brand_name)
                else:
                    html = render_tips_slide_dark(theme, slide, i, total, brand_name)

            await page.set_content(html, wait_until="networkidle")
            await asyncio.sleep(0.8)

            out_path = slide_dir / f"slide_{i+1:02d}.png"
            await page.screenshot(path=str(out_path), full_page=False)
            
            # Upload to Cloudinary
            import cloudinary
            import cloudinary.uploader
            import os
            
            upload_res = cloudinary.uploader.upload(str(out_path), folder=f"carousel_output/{content_id}")
            output_paths.append(upload_res["secure_url"])
            
            # Delete local file after upload
            os.remove(out_path)

        await browser.close()
        
    try:
        import shutil
        shutil.rmtree(slide_dir, ignore_errors=True)
    except:
        pass

    return output_paths

def render_carousel_sync(content_id: int, carousel_data: Dict[str, Any], template_id: int = None, brand_name: str = "zayedtech", custom_text_color: str = None, custom_accent_color: str = None) -> List[str]:
    return asyncio.run(render_carousel_images(content_id, carousel_data, brand_name, template_id, custom_text_color, custom_accent_color))
