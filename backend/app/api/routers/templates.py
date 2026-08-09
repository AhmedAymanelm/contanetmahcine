import os
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session
import fitz  # PyMuPDF
from app.api.deps import get_db
from app.models.carousel_template import CarouselTemplate

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()
cloudinary.config() # Automatically picks up CLOUDINARY_URL from env

router = APIRouter()
TEMPLATES_DIR = Path("static/templates")

@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    style_mode: str = Form("glass_mixed"),
    db: Session = Depends(get_db)
):
    ext = file.filename.lower().split('.')[-1]
    if ext not in ["pdf", "png", "jpg", "jpeg"]:
        raise HTTPException(status_code=400, detail="Only PDF or Image files are allowed")

    # Save temp file
    temp_path = TEMPLATES_DIR / "temp" / file.filename
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        # Create template record in DB to get ID first
        new_template = CarouselTemplate(
            name=name,
            style_mode=style_mode
        )
        db.add(new_template)
        db.commit()
        db.refresh(new_template)

        # Create folder for this template's images
        tpl_dir = TEMPLATES_DIR / str(new_template.id)
        tpl_dir.mkdir(parents=True, exist_ok=True)

        bg_paths = []

        if ext == "pdf":
            # Open PDF and verify it has at least 1 page
            doc = fitz.open(temp_path)
            if len(doc) == 0:
                raise HTTPException(status_code=400, detail="PDF has no pages")

            # Extract up to 3 pages (Cover, Body, CTA)
            zoom = 2.0  # Increase resolution for better background quality
            mat = fitz.Matrix(zoom, zoom)
            
            for i in range(min(3, len(doc))):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=mat)
                img_name = f"bg_{i}.png"
                img_path = tpl_dir / img_name
                pix.save(str(img_path))
                bg_paths.append(f"/static/templates/{new_template.id}/{img_name}")
        else:
            # It's an image
            from PIL import Image
            img_name = "bg_0.png"
            img_path = tpl_dir / img_name
            with Image.open(temp_path) as img:
                # Convert to RGB to ensure png works cleanly if it's jpg
                if img.mode != 'RGB' and img.mode != 'RGBA':
                    img = img.convert('RGBA')
                img.save(str(img_path), format="PNG")
            bg_paths.append(f"/static/templates/{new_template.id}/{img_name}")

        # If we have less than 3 pages/images, duplicate the last available one
        while len(bg_paths) < 3:
            bg_paths.append(bg_paths[-1])

        new_template.cover_bg_path = bg_paths[0]
        new_template.body_bg_path = bg_paths[1]
        new_template.cta_bg_path = bg_paths[2]
        
        # --- AI COLOR EXTRACTION ---
        try:
            import colorgram
            cover_abs_path = TEMPLATES_DIR / str(new_template.id) / "bg_0.png"
            colors = colorgram.extract(str(cover_abs_path), 5)
            
            if colors:
                bg_color = colors[0]
                r, g, b = bg_color.rgb.r, bg_color.rgb.g, bg_color.rgb.b
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                
                if luminance < 0.5:
                    new_template.text_color = "#ffffff"
                    new_template.accent_color = "#facc15" # Default gold
                    for c in colors[1:]:
                        c_lum = (0.299 * c.rgb.r + 0.587 * c.rgb.g + 0.114 * c.rgb.b) / 255
                        if c_lum > 0.5 and (abs(c.rgb.r - r) > 40 or abs(c.rgb.g - g) > 40):
                            new_template.accent_color = f"#{c.rgb.r:02x}{c.rgb.g:02x}{c.rgb.b:02x}"
                            break
                else:
                    new_template.text_color = "#121212"
                    new_template.accent_color = "#1e3a8a" # Default blue
                    for c in colors[1:]:
                        c_lum = (0.299 * c.rgb.r + 0.587 * c.rgb.g + 0.114 * c.rgb.b) / 255
                        if c_lum < 0.4 and (abs(c.rgb.r - r) > 40 or abs(c.rgb.g - g) > 40):
                            new_template.accent_color = f"#{c.rgb.r:02x}{c.rgb.g:02x}{c.rgb.b:02x}"
                            break
        except Exception as e:
            print("Color extraction failed:", e)
            new_template.text_color = "#ffffff"
            new_template.accent_color = "#3b82f6"
            
        # --- CLOUDINARY UPLOAD ---
        cloud_bg_paths = []
        for local_bg in bg_paths:
            # local_bg is like "/static/templates/1/bg_0.png"
            local_path_full = str(Path(local_bg.strip("/")))
            upload_result = cloudinary.uploader.upload(local_path_full, folder=f"templates/{new_template.id}")
            cloud_bg_paths.append(upload_result["secure_url"])
            
        new_template.cover_bg_path = cloud_bg_paths[0]
        new_template.body_bg_path = cloud_bg_paths[1]
        new_template.cta_bg_path = cloud_bg_paths[2]
            
        db.commit()
    finally:
        # Cleanup temp
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {"detail": "Template created successfully", "id": new_template.id}

@router.get("/")
def get_templates(db: Session = Depends(get_db)):
    templates = db.query(CarouselTemplate).order_by(CarouselTemplate.id.desc()).all()
    return templates

@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(CarouselTemplate).filter(CarouselTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    # Delete from DB
    db.delete(template)
    db.commit()
    
    # Delete folder
    tpl_dir = TEMPLATES_DIR / str(template_id)
    if tpl_dir.exists():
        import shutil
        shutil.rmtree(tpl_dir, ignore_errors=True)
        
    return {"detail": "Template deleted successfully"}
