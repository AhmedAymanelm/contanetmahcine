from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.api.deps import get_db
from app.models.source import Source
from app.models.raw_article import RawArticle
from app.models.content_item import ContentItem

router = APIRouter()

from sqlalchemy import func

@router.get("/")
def get_dashboard_stats(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    
    total_articles = db.query(RawArticle).filter(func.lower(RawArticle.status) == 'pending').count()
    
    # 2. Pending Reviews
    pending_count = db.query(ContentItem).filter(func.lower(ContentItem.status) == 'pending_review').count()
    
    # 3. Approved
    approved_count = db.query(ContentItem).filter(func.lower(ContentItem.status) == 'approved').count()
    total_content = db.query(ContentItem).count()
    approval_rate = int((approved_count / total_content * 100)) if total_content > 0 else 0
    
    # 4. Scheduled
    scheduled_count = db.query(ContentItem).filter(func.lower(ContentItem.status) == 'scheduled').count()
    
    # Recent Content (latest 5)
    recent_content = db.query(ContentItem).order_by(ContentItem.created_at.desc()).limit(5).all()
    
    # Pending Content (latest 5)
    pending_content = db.query(ContentItem).filter(func.lower(ContentItem.status) == 'pending_review').order_by(ContentItem.created_at.desc()).limit(5).all()

    # 5. Published and Draft
    published_count = db.query(ContentItem).filter(func.lower(ContentItem.status) == 'published').count()
    draft_count = db.query(RawArticle).filter(func.lower(RawArticle.status) == 'approved_for_generation').count()
    
    total_sources = db.query(Source).count()
    
    # Platform Performance (Engagement/Interactions)
    platforms_count = {"Instagram": 0, "LinkedIn": 0, "Facebook": 0, "X": 0, "Snapchat": 0, "Threads": 0, "TikTok": 0}
    
    # Calculate base performance from published posts
    published_items = db.query(ContentItem).filter(func.lower(ContentItem.status) == 'published').all()
    for item in published_items:
        if item.platforms:
            for p in item.platforms:
                p_upper = p.upper()
                if "IG" in p_upper or "INSTA" in p_upper: platforms_count["Instagram"] += 1
                elif "FB" in p_upper or "FACEBOOK" in p_upper: platforms_count["Facebook"] += 1
                elif "TW" in p_upper or "X" in p_upper or "TWITTER" in p_upper: platforms_count["X"] += 1
                elif "LI" in p_upper or "LINKEDIN" in p_upper: platforms_count["LinkedIn"] += 1
                elif "SC" in p_upper or "SNAP" in p_upper: platforms_count["Snapchat"] += 1
                elif "TH" in p_upper or "THREADS" in p_upper: platforms_count["Threads"] += 1
                elif "TK" in p_upper or "TIKTOK" in p_upper: platforms_count["TikTok"] += 1

    
    # Fetch real Instagram stats
    try:
        from app.core.config import settings
        import httpx
        if settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_ACCOUNT_ID:
            url = f"https://graph.instagram.com/v19.0/{settings.INSTAGRAM_ACCOUNT_ID}/media?fields=like_count,comments_count&access_token={settings.INSTAGRAM_ACCESS_TOKEN}"
            with httpx.Client(timeout=3.0) as client:
                res = client.get(url)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    total_ig_eng = sum(item.get("like_count", 0) + item.get("comments_count", 0) for item in data)
                    platforms_count["Instagram"] += total_ig_eng
    except Exception as e:
        print(f"Error fetching IG stats: {e}")
        
    # Fetch real Facebook stats
    try:
        if settings.FACEBOOK_ACCESS_TOKEN and settings.FACEBOOK_PAGE_ID:
            # Facebook Page Posts engagement
            fb_url = f"https://graph.facebook.com/v19.0/{settings.FACEBOOK_PAGE_ID}/posts?fields=likes.summary(true),comments.summary(true)&access_token={settings.FACEBOOK_ACCESS_TOKEN}"
            with httpx.Client(timeout=3.0) as client:
                fb_res = client.get(fb_url)
                if fb_res.status_code == 200:
                    fb_data = fb_res.json().get("data", [])
                    total_fb_eng = 0
                    for post in fb_data:
                        likes = post.get("likes", {}).get("summary", {}).get("total_count", 0)
                        comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
                        total_fb_eng += (likes + comments)
                    platforms_count["Facebook"] += total_fb_eng
    except Exception as e:
        print(f"Error fetching FB stats: {e}")
    
    return {
        "stats": {
            "articles_today": total_articles,
            "pending_reviews": pending_count,
            "approval_rate": f"{approval_rate}%",
            "scheduled": scheduled_count
        },
        "sidebar_counts": {
            "sources": total_sources,
            "raw_articles": total_articles,
            "content": total_content,
            "review": pending_count
        },
        "pipeline_counts": {
            "raw": total_articles,
            "draft": draft_count,
            "review": pending_count,
            "scheduled": scheduled_count,
            "published": published_count
        },
        "platform_performance": platforms_count,
        "recent_content": [
            {
                "id": c.id,
                "title": c.raw_article.title if c.raw_article else "بدون عنوان",
                "source_name": c.raw_article.source.name if c.raw_article and c.raw_article.source else "مصدر مجهول",
                "content_type": c.content_type,
                "status": c.status,
                "platforms": c.platforms if c.platforms else []
            }
            for c in recent_content
        ],
        "pending_content": [
             {
                "id": c.id,
                "title": c.raw_article.title if c.raw_article else "بدون عنوان",
                "source_name": c.raw_article.source.name if c.raw_article and c.raw_article.source else "مصدر مجهول",
                "content_type": c.content_type,
                "platforms": c.platforms if c.platforms else []
            }
            for c in pending_content
        ]
    }
