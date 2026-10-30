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

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[VisualTemplateResponse])
async def list_visual_templates(db: Session = Depends(get_db)):
    """List all visual templates."""
    return db.query(VisualTemplate).order_by(VisualTemplate.id).all()


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
