"""
Analytics API — comprehensive statistics for the Content Machine dashboard.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from app.api.deps import get_db
from app.models.raw_article import RawArticle
from app.models.content_item import ContentItem
from app.models.source import Source

router = APIRouter()


def _platform_label(p: str) -> str:
    p = p.upper()
    if "IG" in p or "INSTAGRAM" in p:
        return "Instagram"
    if "FB" in p or "FACEBOOK" in p:
        return "Facebook"
    if "LI" in p or "LINKEDIN" in p:
        return "LinkedIn"
    if "TW" in p or "TWITTER" in p or p == "X":
        return "X (Twitter)"
    if "TT" in p or "TIKTOK" in p:
        return "TikTok"
    if "TH" in p or "THREADS" in p:
        return "Threads"
    if "SC" in p or "SNAPCHAT" in p:
        return "Snapchat"
    return p.title()


@router.get("/overview")
def get_analytics_overview(db: Session = Depends(get_db)):
    """Full analytics overview: scraping, content, platforms, timeline."""
    now = datetime.now(timezone.utc)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)

    # 1. Scraping stats
    total_scraped = db.query(RawArticle).count()
    scraped_7d = db.query(RawArticle).filter(RawArticle.created_at >= last_7d).count()
    scraped_30d = db.query(RawArticle).filter(RawArticle.created_at >= last_30d).count()
    total_sources = db.query(Source).count()
    active_sources = db.query(Source).filter(Source.is_active == True).count()

    # 2. Content pipeline
    all_content = db.query(ContentItem).all()
    total_content = len(all_content)

    status_counts = defaultdict(int)
    type_counts = defaultdict(int)
    platform_counts = defaultdict(int)
    published_items = []

    for item in all_content:
        status_key = (item.status or "UNKNOWN").upper()
        status_counts[status_key] += 1
        type_counts[(item.content_type or "UNKNOWN").upper()] += 1
        platforms = item.platforms or []
        if isinstance(platforms, str):
            platforms = [platforms]
        for p in platforms:
            platform_counts[_platform_label(p)] += 1
        if status_key == "PUBLISHED":
            published_items.append(item)

    published_count = len(published_items)
    approval_rate = round(
        (status_counts.get("APPROVED", 0) + published_count) / total_content * 100
    ) if total_content > 0 else 0

    # 3. Published per platform
    pub_per_platform = defaultdict(int)
    for item in published_items:
        platforms = item.platforms or []
        if isinstance(platforms, str):
            platforms = [platforms]
        for p in platforms:
            pub_per_platform[_platform_label(p)] += 1

    # 4. Daily scraping trend (last 14 days)
    daily_scrape = []
    for i in range(13, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(RawArticle).filter(
            RawArticle.created_at >= day_start,
            RawArticle.created_at < day_end
        ).count()
        daily_scrape.append({"date": day_start.strftime("%d/%m"), "articles": count})

    # 5. Daily content generation trend (last 14 days)
    daily_content = []
    for i in range(13, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(ContentItem).filter(
            ContentItem.created_at >= day_start,
            ContentItem.created_at < day_end
        ).count()
        daily_content.append({"date": day_start.strftime("%d/%m"), "content": count})

    # 6. Top sources by article count
    source_rows = (
        db.query(Source.name, func.count(RawArticle.id).label("cnt"))
        .join(RawArticle, RawArticle.source_id == Source.id, isouter=True)
        .group_by(Source.id, Source.name)
        .order_by(func.count(RawArticle.id).desc())
        .limit(8)
        .all()
    )
    top_sources = [{"source": row[0], "articles": row[1]} for row in source_rows]

    # 7. Top published content (most recent)
    top_content = []
    for item in sorted(published_items, key=lambda x: x.created_at or datetime.min, reverse=True)[:10]:
        raw = item.raw_article
        title = raw.title if raw else (
            (item.generated_content or {}).get("title", "Untitled")
            if isinstance(item.generated_content, dict) else "Untitled"
        )
        platforms = item.platforms or []
        if isinstance(platforms, str):
            platforms = [platforms]
        top_content.append({
            "id": item.id,
            "title": title[:80],
            "type": item.content_type,
            "platforms": [_platform_label(p) for p in platforms],
            "published_at": (item.published_at or item.created_at).isoformat() if (item.published_at or item.created_at) else None,
        })

    # 8. Published by content type
    pub_by_type = defaultdict(int)
    for item in published_items:
        pub_by_type[(item.content_type or "UNKNOWN").upper()] += 1

    return {
        "scraping": {
            "total_scraped": total_scraped,
            "scraped_7d": scraped_7d,
            "scraped_30d": scraped_30d,
            "total_sources": total_sources,
            "active_sources": active_sources,
        },
        "pipeline": {
            "total_content": total_content,
            "published": published_count,
            "scheduled": status_counts.get("SCHEDULED", 0),
            "pending_review": status_counts.get("PENDING_REVIEW", 0),
            "approved": status_counts.get("APPROVED", 0),
            "rejected": status_counts.get("REJECTED", 0),
            "draft": status_counts.get("DRAFT", 0),
            "approval_rate": approval_rate,
        },
        "platforms": {
            "total_posts_per_platform": dict(platform_counts),
            "published_per_platform": dict(pub_per_platform),
        },
        "content_types": [{"type": k, "count": v} for k, v in type_counts.items()],
        "published_by_type": dict(pub_by_type),
        "trends": {
            "daily_scrape": daily_scrape,
            "daily_content": daily_content,
        },
        "top_sources": top_sources,
        "top_content": top_content,
    }
