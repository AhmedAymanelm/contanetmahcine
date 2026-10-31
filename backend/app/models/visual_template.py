from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from app.models.base import Base


class VisualTemplate(Base):
    __tablename__ = "visual_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    template_type = Column(String, default="REEL")  # "REEL" or "CAROUSEL"

    # Background
    bg_type = Column(String, default="gradient")  # "gradient", "solid", "image"
    bg_color1 = Column(String, default="#0a0a0a")
    bg_color2 = Column(String, default="#1a0a00")
    bg_image_url = Column(String, nullable=True)

    # Text styling
    text_color = Column(String, default="#ffffff")
    accent_color = Column(String, default="#FF5C00")
    font_size = Column(Integer, default=42)
    font_weight = Column(String, default="900")

    # Animation
    animation = Column(String, default="slideUp")  # "slideUp", "fadeIn", "scaleIn", "slideLeft"

    # Layout
    text_align = Column(String, default="center")

    # Preview (base64 thumbnail or URL)
    thumbnail_url = Column(String, nullable=True)

    # Multi-slide configurations (JSON array of slide styles: [{bg_type, bg_color1, bg_color2, accent_color, text_color, animation, font_size, text_align, title, sample_text}, ...])
    slides_json = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

