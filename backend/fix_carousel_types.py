"""
One-time fix: revert items incorrectly changed from POST to CAROUSEL.
These are CAROUSEL items whose platforms contain FB or X (not just Li/IG).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.session import SessionLocal
from app.models.content_item import ContentItem
from sqlalchemy.orm.attributes import flag_modified
import json

db = SessionLocal()

# Find CAROUSEL items whose platforms suggest they were originally POST
items = db.query(ContentItem).filter(ContentItem.content_type == "CAROUSEL").all()
fixed = 0
for item in items:
    plats = item.platforms or []
    if isinstance(plats, str):
        plats = [p.strip() for p in plats.split(',')]
    plat_set = set(plats)
    # If it has FB or X but NOT IG, it was likely converted from POST
    if ('FB' in plat_set or 'X' in plat_set) and 'IG' not in plat_set:
        gen = item.generated_content or {}
        if isinstance(gen, str):
            try: gen = json.loads(gen)
            except: continue
        # Only revert if it has slides but NOT the original carousel structure
        # (real carousels would have been created by the AI as CAROUSEL type originally)
        if 'slides' in gen and 'unified_post' not in gen and '_carousel_slides' not in gen:
            print(f"Fixing item {item.id}: platforms={item.platforms}, type CAROUSEL -> POST")
            # Restore minimal POST structure from the slide content
            slide_texts = [s.get('heading','') for s in gen.get('slides',[])]
            restored_text = ' '.join(slide_texts)
            gen['unified_post'] = restored_text
            gen['_restored_from_carousel'] = True
            item.content_type = "POST"
            item.generated_content = gen
            flag_modified(item, "generated_content")
            fixed += 1

db.commit()
db.close()
print(f"\nFixed {fixed} item(s) successfully.")
