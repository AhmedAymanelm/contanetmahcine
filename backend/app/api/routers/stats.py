from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.api.deps import get_db
from app.models.source import Source
from app.models.raw_article import RawArticle
from app.models.content_item import ContentItem

router = APIRouter()

from sqlalchemy import func
import httpx
from app.core.config import settings

@router.get("/debug/facebook")
def debug_facebook_api():
    if not settings.FACEBOOK_ACCESS_TOKEN or not settings.FACEBOOK_PAGE_ID:
        return {"error": "Missing Facebook credentials in environment"}
    
    fb_url = f"https://graph.facebook.com/v19.0/{settings.FACEBOOK_PAGE_ID}/posts?fields=likes.summary(true),comments.summary(true)&access_token={settings.FACEBOOK_ACCESS_TOKEN}"
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.get(fb_url)
            return {
                "status_code": res.status_code,
                "response": res.json()
            }
    except Exception as e:
        return {"error": str(e)}

@router.get("/")
def get_dashboard_stats(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    # Expire old pending content globally
    db.query(ContentItem).filter(
        func.lower(ContentItem.status) == 'pending_review',
        ContentItem.created_at < cutoff
    ).update({"status": "EXPIRED"}, synchronize_session=False)
    db.commit()

    total_articles = db.query(RawArticle).filter(
        func.lower(RawArticle.status) == 'pending'
    ).count()
    
    # 2. Pending Reviews
    pending_count = db.query(ContentItem).filter(
        func.lower(ContentItem.status) == 'pending_review'
    ).count()
    
    # 3. Approved
    approved_count = db.query(ContentItem).filter(
        func.lower(ContentItem.status) == 'approved'
    ).count()
    total_content = db.query(ContentItem).count()
    approval_rate = int((approved_count / total_content * 100)) if total_content > 0 else 0
    
    # 4. Scheduled
    scheduled_count = db.query(ContentItem).filter(
        func.lower(ContentItem.status) == 'scheduled'
    ).count()
    
    # Recent Content (latest 5)
    recent_content = db.query(ContentItem).order_by(ContentItem.created_at.desc()).limit(5).all()
    
    # Pending Content (latest 5)
    pending_content = db.query(ContentItem).filter(
        func.lower(ContentItem.status) == 'pending_review'
    ).order_by(ContentItem.created_at.desc()).limit(5).all()

    # 5. Published and Draft
    published_count = db.query(ContentItem).filter(
        func.lower(ContentItem.status) == 'published'
    ).count()
    raw_drafts = db.query(RawArticle).filter(
        func.lower(RawArticle.status) == 'approved_for_generation'
    ).count()
    
    content_drafts = db.query(ContentItem).filter(
        func.lower(ContentItem.status) == 'draft'
    ).count()
    
    draft_count = raw_drafts + content_drafts
    
    total_sources = db.query(Source).count()
    
    # Platform Performance (Engagement/Interactions)
    platforms_count = {"Instagram": 0, "Facebook": 0}
    
    # Calculate base performance from published posts (for platforms without API)
    # The user requested to ONLY show real API engagement, so we do not add +1 per post anymore.
    pass

    
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
    
    # Last Ingestion Time
    last_article = db.query(RawArticle).order_by(RawArticle.created_at.desc()).first()
    last_ingestion_time = last_article.created_at.isoformat() if last_article and last_article.created_at else None

    return {
        "stats": {
            "articles_today": total_articles,
            "pending_reviews": pending_count,
            "approval_rate": f"{approval_rate}%",
            "scheduled": scheduled_count,
            "last_ingestion_time": last_ingestion_time
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
