"""
Analytics API — comprehensive statistics with filters.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional
import io, csv
from app.api.deps import get_db
from app.models.raw_article import RawArticle
from app.models.content_item import ContentItem
from app.models.source import Source

router = APIRouter()


def _platform_label(p: str) -> str:
    p = p.upper()
    if "IG" in p or "INSTAGRAM" in p: return "Instagram"
    if "FB" in p or "FACEBOOK" in p:  return "Facebook"
    if "LI" in p or "LINKEDIN" in p:  return "LinkedIn"
    if "TW" in p or "TWITTER" in p or p == "X": return "X (Twitter)"
    if "TT" in p or "TIKTOK" in p:   return "TikTok"
    if "TH" in p or "THREADS" in p:  return "Threads"
    if "SC" in p or "SNAPCHAT" in p: return "Snapchat"
    return p.title()


def _get_window(days: int, now: datetime):
    """Return (start, prev_start) for current and previous period."""
    start = now - timedelta(days=days) if days > 0 else datetime(2000, 1, 1, tzinfo=timezone.utc)
    prev_start = start - timedelta(days=days) if days > 0 else start
    return start, prev_start


@router.get("/overview")
def get_analytics_overview(
    db: Session = Depends(get_db),
    days: int = Query(30, description="0=all time, else last N days"),
    platform: Optional[str] = Query(None, description="Filter by platform label"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    source_id: Optional[int] = Query(None, description="Filter by source ID"),
):
    now = datetime.now(timezone.utc)
    window_start, prev_start = _get_window(days, now)
    last_7d = now - timedelta(days=7)

    # ── Scraping stats ─────────────────────────────────────────────────────
    scrape_q = db.query(RawArticle)
    if source_id:
        scrape_q = scrape_q.filter(RawArticle.source_id == source_id)
    if days > 0:
        scrape_q = scrape_q.filter(RawArticle.created_at >= window_start)

    total_scraped = scrape_q.count()
    scraped_7d    = scrape_q.filter(RawArticle.created_at >= last_7d).count() if days == 0 or days >= 7 else total_scraped
    total_sources  = db.query(Source).count()
    active_sources = db.query(Source).filter(Source.is_active == True).count()

    # ── Content items (apply filters) ─────────────────────────────────────
    all_q = db.query(ContentItem)
    if days > 0:
        all_q = all_q.filter(ContentItem.created_at >= window_start)
    if content_type:
        all_q = all_q.filter(func.upper(ContentItem.content_type) == content_type.upper())

    all_content = all_q.all()

    # Apply platform filter post-query (platforms stored as JSON array)
    if platform:
        all_content = [
            c for c in all_content
            if any(_platform_label(p) == platform for p in (c.platforms or []))
        ]

    total_content = len(all_content)
    status_counts = defaultdict(int)
    type_counts   = defaultdict(int)
    platform_counts = defaultdict(int)
    published_items = []
    peak_hours  = defaultdict(int)   # hour → count
    peak_days   = defaultdict(int)   # weekday (0=Mon) → count

    for item in all_content:
        sk = (item.status or "UNKNOWN").upper()
        status_counts[sk] += 1
        type_counts[(item.content_type or "UNKNOWN").upper()] += 1
        platforms = item.platforms or []
        if isinstance(platforms, str): platforms = [platforms]
        for p in platforms:
            platform_counts[_platform_label(p)] += 1
        if sk == "PUBLISHED":
            published_items.append(item)
            ts = item.published_at or item.created_at
            if ts:
                peak_hours[ts.hour] += 1
                peak_days[ts.weekday()] += 1

    published_count = len(published_items)
    approval_rate   = round(
        (status_counts.get("APPROVED", 0) + published_count) / total_content * 100
    ) if total_content > 0 else 0

    # ── Previous period for comparison ────────────────────────────────────
    if days > 0:
        prev_q = db.query(ContentItem).filter(
            ContentItem.created_at >= prev_start,
            ContentItem.created_at < window_start,
            func.upper(ContentItem.status) == "PUBLISHED"
        )
        if content_type:
            prev_q = prev_q.filter(func.upper(ContentItem.content_type) == content_type.upper())
        prev_published = prev_q.all()
        if platform:
            prev_published = [c for c in prev_published
                              if any(_platform_label(p) == platform for p in (c.platforms or []))]
        prev_published_count = len(prev_published)
    else:
        prev_published_count = 0

    # ── Published per platform ─────────────────────────────────────────────
    pub_per_platform = defaultdict(int)
    for item in published_items:
        platforms = item.platforms or []
        if isinstance(platforms, str): platforms = [platforms]
        for p in platforms:
            pub_per_platform[_platform_label(p)] += 1

    # ── Daily trends (variable granularity) ───────────────────────────────
    trend_days = min(days if days > 0 else 30, 30)
    daily_scrape   = []
    daily_content  = []
    for i in range(trend_days - 1, -1, -1):
        day = now - timedelta(days=i)
        ds  = day.replace(hour=0, minute=0, second=0, microsecond=0)
        de  = ds + timedelta(days=1)
        s_q = db.query(RawArticle).filter(RawArticle.created_at >= ds, RawArticle.created_at < de)
        if source_id: s_q = s_q.filter(RawArticle.source_id == source_id)
        c_q = db.query(ContentItem).filter(ContentItem.created_at >= ds, ContentItem.created_at < de)
        if content_type: c_q = c_q.filter(func.upper(ContentItem.content_type) == content_type.upper())
        daily_scrape.append({"date": ds.strftime("%d/%m"), "articles": s_q.count()})
        daily_content.append({"date": ds.strftime("%d/%m"), "content": c_q.count()})

    # ── Top sources ────────────────────────────────────────────────────────
    src_q = (
        db.query(Source.id, Source.name, func.count(RawArticle.id).label("cnt"))
        .join(RawArticle, RawArticle.source_id == Source.id, isouter=True)
        .group_by(Source.id, Source.name)
        .order_by(func.count(RawArticle.id).desc())
        .limit(8)
    )
    top_sources = [{"id": r[0], "source": r[1], "articles": r[2]} for r in src_q.all()]

    # ── Top content (published) ────────────────────────────────────────────
    top_content_list = []
    for item in sorted(published_items, key=lambda x: x.created_at or datetime.min, reverse=True)[:15]:
        raw   = item.raw_article
        title = raw.title if raw else (
            (item.generated_content or {}).get("title", "Untitled")
            if isinstance(item.generated_content, dict) else "Untitled"
        )
        platforms = item.platforms or []
        if isinstance(platforms, str): platforms = [platforms]
        top_content_list.append({
            "id": item.id,
            "title": title[:80],
            "type": item.content_type,
            "platforms": [_platform_label(p) for p in platforms],
            "published_at": (item.published_at or item.created_at).isoformat() if (item.published_at or item.created_at) else None,
            "source": raw.source.name if raw and raw.source else "—",
        })

    # ── Top performer (source that generated most published content) ────────
    src_pub_count = defaultdict(lambda: {"name": "", "count": 0})
    for item in published_items:
        raw = item.raw_article
        if raw and raw.source:
            src_pub_count[raw.source_id]["name"]  = raw.source.name
            src_pub_count[raw.source_id]["count"] += 1
    top_performer = max(src_pub_count.values(), key=lambda x: x["count"]) if src_pub_count else None

    # ── Peak hours array (24 slots) ───────────────────────────────────────
    peak_hours_arr = [{"hour": h, "count": peak_hours.get(h, 0)} for h in range(24)]
    DAY_NAMES = ["الإثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
    peak_days_arr = [{"day": DAY_NAMES[d], "count": peak_days.get(d, 0)} for d in range(7)]

    # ── Approval funnel ────────────────────────────────────────────────────
    funnel = [
        {"label": "أخبار مسحوبة",    "value": total_scraped},
        {"label": "محتوى مُنشأ",      "value": total_content},
        {"label": "قيد المراجعة",     "value": status_counts.get("PENDING_REVIEW", 0) + published_count + status_counts.get("APPROVED", 0)},
        {"label": "معتمد",            "value": status_counts.get("APPROVED", 0) + published_count},
        {"label": "منشور",            "value": published_count},
    ]

    return {
        "filters_applied": {
            "days": days, "platform": platform,
            "content_type": content_type, "source_id": source_id,
        },
        "scraping": {
            "total_scraped": total_scraped,
            "scraped_7d": scraped_7d,
            "total_sources": total_sources,
            "active_sources": active_sources,
        },
        "pipeline": {
            "total_content": total_content,
            "published": published_count,
            "prev_published": prev_published_count,
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
        "trends": {
            "daily_scrape": daily_scrape,
            "daily_content": daily_content,
        },
        "peak_hours": peak_hours_arr,
        "peak_days": peak_days_arr,
        "funnel": funnel,
        "top_sources": top_sources,
        "top_content": top_content_list,
        "top_performer": top_performer,
    }


@router.get("/export-csv")
def export_csv(
    db: Session = Depends(get_db),
    days: int = Query(30),
):
    """Export published content as CSV."""
    now = datetime.now(timezone.utc)
    window_start, _ = _get_window(days, now)
    q = db.query(ContentItem).filter(func.upper(ContentItem.status) == "PUBLISHED")
    if days > 0:
        q = q.filter(ContentItem.created_at >= window_start)
    items = q.order_by(ContentItem.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Type", "Platforms", "Published At", "Source"])
    for item in items:
        raw   = item.raw_article
        title = raw.title if raw else "—"
        platforms = item.platforms or []
        if isinstance(platforms, str): platforms = [platforms]
        writer.writerow([
            item.id, title, item.content_type,
            " | ".join([_platform_label(p) for p in platforms]),
            (item.published_at or item.created_at).isoformat() if (item.published_at or item.created_at) else "",
            raw.source.name if raw and raw.source else "—",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=content_machine_{days}d.csv"}
    )


@router.get("/sources-list")
def get_sources_list(db: Session = Depends(get_db)):
    """Return all sources for the filter dropdown."""
    sources = db.query(Source.id, Source.name).order_by(Source.name).all()
    return [{"id": r[0], "name": r[1]} for r in sources]


@router.get("/top-engagement")
def get_top_engagement():
    """
    Fetch real per-post engagement from Instagram + Facebook APIs.
    Returns all posts ranked by total interactions (likes + comments).
    """
    import httpx
    from app.core.config import settings

    posts = []
    errors = []

    # ── Instagram ─────────────────────────────────────────────────────────────
    if settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_ACCOUNT_ID:
        try:
            fields = "id,caption,media_type,media_url,thumbnail_url,timestamp,like_count,comments_count,permalink"
            url = (
                f"https://graph.instagram.com/v19.0/{settings.INSTAGRAM_ACCOUNT_ID}/media"
                f"?fields={fields}&limit=50&access_token={settings.INSTAGRAM_ACCESS_TOKEN}"
            )
            with httpx.Client(timeout=8.0) as client:
                res = client.get(url)
            if res.status_code == 200:
                for item in res.json().get("data", []):
                    likes    = item.get("like_count", 0) or 0
                    comments = item.get("comments_count", 0) or 0
                    caption  = (item.get("caption") or "")[:120]
                    thumb    = item.get("media_url") or item.get("thumbnail_url") or ""
                    posts.append({
                        "platform":    "Instagram",
                        "post_id":     item.get("id"),
                        "caption":     caption,
                        "likes":       likes,
                        "comments":    comments,
                        "total":       likes + comments,
                        "media_type":  item.get("media_type", ""),
                        "thumbnail":   thumb,
                        "permalink":   item.get("permalink", ""),
                        "timestamp":   item.get("timestamp", ""),
                    })
            else:
                errors.append(f"Instagram API {res.status_code}: {res.text[:200]}")
        except Exception as e:
            errors.append(f"Instagram error: {str(e)}")

    # ── Facebook ──────────────────────────────────────────────────────────────
    if settings.FACEBOOK_ACCESS_TOKEN and settings.FACEBOOK_PAGE_ID:
        try:
            fields = "id,message,story,created_time,likes.summary(true),comments.summary(true),full_picture,permalink_url"
            fb_url = (
                f"https://graph.facebook.com/v19.0/{settings.FACEBOOK_PAGE_ID}/posts"
                f"?fields={fields}&limit=50&access_token={settings.FACEBOOK_ACCESS_TOKEN}"
            )
            with httpx.Client(timeout=8.0) as client:
                fb_res = client.get(fb_url)
            if fb_res.status_code == 200:
                for item in fb_res.json().get("data", []):
                    likes    = item.get("likes",    {}).get("summary", {}).get("total_count", 0) or 0
                    comments = item.get("comments", {}).get("summary", {}).get("total_count", 0) or 0
                    caption  = (item.get("message") or item.get("story") or "")[:120]
                    posts.append({
                        "platform":    "Facebook",
                        "post_id":     item.get("id"),
                        "caption":     caption,
                        "likes":       likes,
                        "comments":    comments,
                        "total":       likes + comments,
                        "media_type":  "POST",
                        "thumbnail":   item.get("full_picture", ""),
                        "permalink":   item.get("permalink_url", ""),
                        "timestamp":   item.get("created_time", ""),
                    })
            else:
                errors.append(f"Facebook API {fb_res.status_code}: {fb_res.text[:200]}")
        except Exception as e:
            errors.append(f"Facebook error: {str(e)}")

    # ── Sort & return ──────────────────────────────────────────────────────────
    posts.sort(key=lambda x: x["total"], reverse=True)

    # Top post
    top_post = posts[0] if posts else None

    # Summary per platform
    platform_summary = {}
    for p in posts:
        pl = p["platform"]
        if pl not in platform_summary:
            platform_summary[pl] = {"posts": 0, "total_likes": 0, "total_comments": 0}
        platform_summary[pl]["posts"]          += 1
        platform_summary[pl]["total_likes"]    += p["likes"]
        platform_summary[pl]["total_comments"] += p["comments"]

    return {
        "top_post":         top_post,
        "all_posts":        posts[:20],          # top 20 ranked
        "platform_summary": platform_summary,
        "total_fetched":    len(posts),
        "errors":           errors,
    }
