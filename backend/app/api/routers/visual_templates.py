import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.api.deps import get_db
from app.models.visual_template import VisualTemplate

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class VisualTemplateCreate(BaseModel):
    name: str
    template_type: str = "REEL"
    bg_type: str = "gradient"
    bg_color1: str = "#0a0a0a"
    bg_color2: str = "#1a0a00"
    bg_image_url: Optional[str] = None
    text_color: str = "#ffffff"
    accent_color: str = "#FF5C00"
    font_size: int = 42
    font_weight: str = "900"
    animation: str = "slideUp"
    text_align: str = "center"
    thumbnail_url: Optional[str] = None
    slides_json: Optional[str] = None


class VisualTemplateUpdate(BaseModel):
    name: Optional[str] = None
    template_type: Optional[str] = None
    bg_type: Optional[str] = None
    bg_color1: Optional[str] = None
    bg_color2: Optional[str] = None
    bg_image_url: Optional[str] = None
    text_color: Optional[str] = None
    accent_color: Optional[str] = None
    font_size: Optional[int] = None
    font_weight: Optional[str] = None
    animation: Optional[str] = None
    text_align: Optional[str] = None
    thumbnail_url: Optional[str] = None
    slides_json: Optional[str] = None


class VisualTemplateResponse(BaseModel):
    id: int
    name: str
    template_type: str
    bg_type: str
    bg_color1: str
    bg_color2: str
    bg_image_url: Optional[str]
    text_color: str
    accent_color: str
    font_size: int
    font_weight: str
    animation: str
    text_align: str
    thumbnail_url: Optional[str]
    slides_json: Optional[str] = None

    class Config:
        from_attributes = True


DEFAULT_TEMPLATES = [
    {
        "name": "زايد تيك - البرتقالي الناري (ZayedTech Flame)",
        "template_type": "REEL",
        "bg_type": "gradient",
        "bg_color1": "#0a0a0a",
        "bg_color2": "#240a00",
        "text_color": "#ffffff",
        "accent_color": "#FF5C00",
        "font_size": 42,
        "font_weight": "900",
        "animation": "slideUp",
        "text_align": "center",
    },
    {
        "name": "سايبر نيون البنفسجي (Cyber Violet)",
        "template_type": "REEL",
        "bg_type": "gradient",
        "bg_color1": "#070514",
        "bg_color2": "#1a0f3c",
        "text_color": "#ffffff",
        "accent_color": "#8B5CF6",
        "font_size": 40,
        "font_weight": "900",
        "animation": "scaleIn",
        "text_align": "center",
    },
    {
        "name": "كاروسيل إنستغرام الزمردي (Emerald Carousel)",
        "template_type": "CAROUSEL",
        "bg_type": "gradient",
        "bg_color1": "#041712",
        "bg_color2": "#0e382c",
        "text_color": "#f8fafc",
        "accent_color": "#10B981",
        "font_size": 38,
        "font_weight": "800",
        "animation": "fadeIn",
        "text_align": "right",
    },
    {
        "name": "كاروسيل جولد الملكي (Royal Gold)",
        "template_type": "CAROUSEL",
        "bg_type": "gradient",
        "bg_color1": "#0c0a02",
        "bg_color2": "#261d06",
        "text_color": "#ffffff",
        "accent_color": "#F59E0B",
        "font_size": 40,
        "font_weight": "900",
        "animation": "slideLeft",
        "text_align": "center",
    },
]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[VisualTemplateResponse])
async def list_visual_templates(db: Session = Depends(get_db)):
    """List all visual templates (auto-seeds defaults if empty and ensures multi-slide deck)."""
    count = db.query(VisualTemplate).count()
    if count == 0:
        for tpl_data in DEFAULT_TEMPLATES:
            db.add(VisualTemplate(**tpl_data))
        db.commit()
    
    templates = db.query(VisualTemplate).order_by(VisualTemplate.id).all()
    # Backfill default multi-slide deck for any template without slides_json
    updated = False
    for tpl in templates:
        if not tpl.slides_json:
            p_accent = tpl.accent_color or "#FF5C00"
            p_c1 = tpl.bg_color1 or "#0a0a0a"
            p_c2 = tpl.bg_color2 or "#240a00"
            default_deck = [
                {"id": 1, "title": "شريحة 1 (الافتتاحية والخطاف)", "bgType": tpl.bg_type or "gradient", "color1": p_c1, "color2": p_c2, "textColor": tpl.text_color or "#ffffff", "accentColor": p_accent, "fontSize": tpl.font_size or 42, "align": tpl.text_align or "center", "animation": tpl.animation or "slideUp", "sampleText": "عوالم الذكاء الاصطناعي تتغير بسرعة غير مسبوقة — هل أنت مستعد؟"},
                {"id": 2, "title": "شريحة 2 (المحتوى والشرح)", "bgType": "gradient", "color1": "#070514", "color2": "#1a0f3c", "textColor": "#ffffff", "accentColor": "#8B5CF6", "fontSize": 38, "align": "center", "animation": "scaleIn", "sampleText": "الشركات التي لا تتبنى الأتمتة الآن ستفقد قدرتها التنافسية خلال شهور."},
                {"id": 3, "title": "شريحة 3 (الخاتمة والتفاعل)", "bgType": "gradient", "color1": "#0c0a02", "color2": "#261d06", "textColor": "#ffffff", "accentColor": "#F59E0B", "fontSize": 40, "align": "center", "animation": "fadeIn", "sampleText": "شاركنا رأيك في التعليقات، وتابع حساب @zayedtech لجديد التقنية!"}
            ]
            tpl.slides_json = json.dumps(default_deck, ensure_ascii=False)
            updated = True
    if updated:
        try:
            db.commit()
        except Exception:
            db.rollback()

    return templates


@router.post("/", response_model=VisualTemplateResponse)
async def create_visual_template(payload: VisualTemplateCreate, db: Session = Depends(get_db)):
    """Create a new visual template."""
    template = VisualTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/{template_id}", response_model=VisualTemplateResponse)
async def update_visual_template(template_id: int, payload: VisualTemplateUpdate, db: Session = Depends(get_db)):
    """Update an existing visual template."""
    template = db.query(VisualTemplate).filter(VisualTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Visual template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
async def delete_visual_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a visual template."""
    template = db.query(VisualTemplate).filter(VisualTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Visual template not found")
    db.delete(template)
    db.commit()
    return {"detail": "Visual template deleted"}

