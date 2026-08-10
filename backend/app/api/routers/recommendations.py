"""
Recommendations API — AI-powered insights for Content Machine.
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
from app.core.config import settings

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


@router.get("/overview")
def get_recommendations(db: Session = Depends(get_db)):
    """
    Full recommendations overview:
    - Source quality scores
    - Platform strategy
    - Best posting times (from published data)
    - Smart alerts
    - Suggested articles for re-publishing
    """
    now = datetime.now(timezone.utc)
    last_30d = now - timedelta(days=30)
    last_7d  = now - timedelta(days=7)
    last_24h = now - timedelta(hours=24)

    # ── 1. Source Quality Scores ───────────────────────────────────────────
    sources = db.query(Source).all()
    source_scores = []
    for src in sources:
        total_scraped = db.query(RawArticle).filter(RawArticle.source_id == src.id).count()
        scraped_30d   = db.query(RawArticle).filter(
            RawArticle.source_id == src.id,
            RawArticle.created_at >= last_30d
        ).count()

        # Content generated from this source
        total_content = db.query(ContentItem).join(
            RawArticle, ContentItem.raw_article_id == RawArticle.id
        ).filter(RawArticle.source_id == src.id).count()

        published_content = db.query(ContentItem).join(
            RawArticle, ContentItem.raw_article_id == RawArticle.id
        ).filter(
            RawArticle.source_id == src.id,
            func.upper(ContentItem.status) == "PUBLISHED"
        ).count()

        # Last scrape activity
        last_article = db.query(RawArticle).filter(
            RawArticle.source_id == src.id
        ).order_by(RawArticle.created_at.desc()).first()
        last_active = last_article.created_at if last_article else None

        # Score: 0-100
        publish_rate  = (published_content / total_content * 50) if total_content > 0 else 0
        activity_score = min(scraped_30d / 30 * 30, 30)   # up to 30 pts for consistent scraping
        size_score     = min(total_scraped / 100 * 20, 20) # up to 20 pts for total volume
        score = round(publish_rate + activity_score + size_score)

        # Alert: silent source (no scrape in 48h but active)
        is_silent = (
            src.is_active and last_active is not None and
            last_active < now - timedelta(hours=48)
        )

        source_scores.append({
            "id":              src.id,
            "name":            src.name,
            "url":             src.url,
            "is_active":       src.is_active,
            "score":           min(score, 100),
            "total_scraped":   total_scraped,
            "scraped_30d":     scraped_30d,
            "total_content":   total_content,
            "published_content": published_content,
            "publish_rate":    round(published_content / total_content * 100) if total_content > 0 else 0,
            "last_active":     last_active.isoformat() if last_active else None,
            "is_silent":       is_silent,
        })

    source_scores.sort(key=lambda x: x["score"], reverse=True)

    # ── 2. Platform Strategy (DB only — fast) ─────────────────────────────
    all_published = db.query(ContentItem).filter(
        func.upper(ContentItem.status) == "PUBLISHED",
        ContentItem.created_at >= last_30d
    ).all()

    platform_stats = defaultdict(lambda: {"posts": 0, "engagement": 0})
    for item in all_published:
        plats = item.platforms or []
        if isinstance(plats, str): plats = [plats]
        for p in plats:
            pl = _platform_label(p)
            platform_stats[pl]["posts"] += 1
    # Note: real engagement data available via /api/analytics/top-engagement

    platform_list = []
    for pl, s in platform_stats.items():
        eng_per_post = round(s["engagement"] / s["posts"], 1) if s["posts"] > 0 else 0
        # Strategy label
        if eng_per_post >= 20:   strategy = "🚀 قوي جداً — ركز هنا"
        elif eng_per_post >= 5:  strategy = "✅ جيد — استمر"
        elif eng_per_post >= 1:  strategy = "⚡ متوسط — حاول تطور"
        else:                    strategy = "⚠️ ضعيف — راجع الاستراتيجية"
        platform_list.append({
            "platform":     pl,
            "posts":        s["posts"],
            "engagement":   s["engagement"],
            "eng_per_post": eng_per_post,
            "strategy":     strategy,
        })
    platform_list.sort(key=lambda x: x["eng_per_post"], reverse=True)

    # ── 3. Best Posting Times ─────────────────────────────────────────────
    peak_hours = defaultdict(int)
    peak_days  = defaultdict(int)
    for item in all_published:
        ts = item.published_at or item.created_at
        if ts:
            peak_hours[ts.hour] += 1
            peak_days[ts.weekday()] += 1

    best_hour = max(peak_hours, key=peak_hours.get) if peak_hours else None
    best_day  = max(peak_days,  key=peak_days.get)  if peak_days  else None
    DAY_AR = ["الإثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]

    best_time_rec = None
    if best_hour is not None and best_day is not None:
        best_time_rec = {
            "hour": best_hour,
            "day": DAY_AR[best_day],
            "day_idx": best_day,
            "posts_at_peak": peak_hours[best_hour],
            "recommendation": f"انشر يوم {DAY_AR[best_day]} الساعة {best_hour}:00 — {peak_hours[best_hour]} بوست نُشروا في هذا الوقت"
        }

    hours_dist = [{"hour": h, "count": peak_hours.get(h, 0)} for h in range(24)]
    days_dist  = [{"day": DAY_AR[d], "count": peak_days.get(d, 0)} for d in range(7)]

    # ── 4. Smart Alerts ────────────────────────────────────────────────────
    alerts = []

    # Silent sources
    silent_sources = [s for s in source_scores if s["is_silent"]]
    if silent_sources:
        names = ", ".join([s["name"] for s in silent_sources[:3]])
        alerts.append({
            "type": "warning",
            "icon": "📡",
            "title": f"مصادر صامتة ({len(silent_sources)})",
            "body": f"{names} لم تُسحب منها أخبار خلال آخر 48 ساعة",
        })

    # Content stuck in review
    stuck_count = db.query(ContentItem).filter(
        func.upper(ContentItem.status) == "PENDING_REVIEW",
        ContentItem.created_at < now - timedelta(hours=12)
    ).count()
    if stuck_count > 0:
        alerts.append({
            "type": "warning",
            "icon": "⏳",
            "title": f"{stuck_count} محتوى عالق في المراجعة",
            "body": "محتوى ينتظر الموافقة أكثر من 12 ساعة — راجع صفحة المراجعة والموافقة",
        })

    # No publishing in 24h
    pub_24h = db.query(ContentItem).filter(
        func.upper(ContentItem.status) == "PUBLISHED",
        ContentItem.created_at >= last_24h
    ).count()
    if pub_24h == 0:
        alerts.append({
            "type": "danger",
            "icon": "🚨",
            "title": "لا يوجد نشر خلال آخر 24 ساعة",
            "body": "لم يُنشر أي محتوى اليوم — راجع الجدول والمواافقات المعلقة",
        })

    # High rejection rate
    total_7d = db.query(ContentItem).filter(ContentItem.created_at >= last_7d).count()
    rejected_7d = db.query(ContentItem).filter(
        func.upper(ContentItem.status) == "REJECTED",
        ContentItem.created_at >= last_7d
    ).count()
    if total_7d > 5 and rejected_7d / total_7d > 0.3:
        alerts.append({
            "type": "warning",
            "icon": "🚫",
            "title": f"معدل رفض مرتفع ({round(rejected_7d/total_7d*100)}%)",
            "body": "أكثر من 30% من المحتوى رُفض هذا الأسبوع — ربما تحتاج لمراجعة إعدادات توليد المحتوى",
        })

    # Low approval rate last 7d
    approved_7d = db.query(ContentItem).filter(
        func.upper(ContentItem.status).in_(["APPROVED","PUBLISHED"]),
        ContentItem.created_at >= last_7d
    ).count()
    if total_7d > 5 and approved_7d / total_7d < 0.2:
        alerts.append({
            "type": "info",
            "icon": "📉",
            "title": "معدل اعتماد منخفض هذا الأسبوع",
            "body": f"فقط {round(approved_7d/total_7d*100)}% من المحتوى اتاعتُمد — راجع جودة المصادر والـ prompts",
        })

    # ── 5. Suggested Articles for Publishing ─────────────────────────────
    # Scraped but not yet turned into content
    suggested = db.query(RawArticle).filter(
        func.lower(RawArticle.status) == "pending",
        RawArticle.created_at >= last_7d
    ).order_by(RawArticle.created_at.desc()).limit(10).all()

    suggested_list = []
    for art in suggested:
        suggested_list.append({
            "id":          art.id,
            "title":       art.title,
            "url":         art.url,
            "source":      art.source.name if art.source else "—",
            "scraped_at":  art.created_at.isoformat() if art.created_at else None,
        })

    # ── 6. Weekly summary stats (for AI prompt) ────────────────────────────
    weekly_stats = {
        "scraped_7d":   db.query(RawArticle).filter(RawArticle.created_at >= last_7d).count(),
        "generated_7d": db.query(ContentItem).filter(ContentItem.created_at >= last_7d).count(),
        "published_7d": pub_24h,
        "top_platform": platform_list[0]["platform"] if platform_list else "—",
        "top_source":   source_scores[0]["name"] if source_scores else "—",
    }

    return {
        "source_scores":     source_scores,
        "platform_strategy": platform_list,
        "best_posting_time": best_time_rec,
        "hours_dist":        hours_dist,
        "days_dist":         days_dist,
        "alerts":            alerts,
        "suggested_articles": suggested_list,
        "weekly_stats":      weekly_stats,
    }


@router.post("/ai-summary")
async def get_ai_summary(db: Session = Depends(get_db)):
    """
    Ask Claude to generate a smart weekly summary + actionable recommendations.
    """
    import anthropic, json

    if not settings.ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY غير مُعيَّن في الإعدادات"}

    now = datetime.now(timezone.utc)
    last_7d = now - timedelta(days=7)

    # Gather stats
    scraped_7d   = db.query(RawArticle).filter(RawArticle.created_at >= last_7d).count()
    generated_7d = db.query(ContentItem).filter(ContentItem.created_at >= last_7d).count()
    published_7d = db.query(ContentItem).filter(
        func.upper(ContentItem.status) == "PUBLISHED",
        ContentItem.created_at >= last_7d
    ).count()
    rejected_7d  = db.query(ContentItem).filter(
        func.upper(ContentItem.status) == "REJECTED",
        ContentItem.created_at >= last_7d
    ).count()

    publish_rate  = round(published_7d / generated_7d * 100) if generated_7d else 0
    rejection_rate = round(rejected_7d / generated_7d * 100) if generated_7d else 0

    # Platform counts
    all_pub = db.query(ContentItem).filter(
        func.upper(ContentItem.status) == "PUBLISHED",
        ContentItem.created_at >= last_7d
    ).all()
    plat_counts = defaultdict(int)
    for item in all_pub:
        plats = item.platforms or []
        if isinstance(plats, str): plats = [plats]
        for p in plats:
            plat_counts[_platform_label(p)] += 1

    top_sources = db.query(Source.name, func.count(RawArticle.id).label("cnt")).join(
        RawArticle, RawArticle.source_id == Source.id, isouter=True
    ).filter(RawArticle.created_at >= last_7d).group_by(Source.id, Source.name).order_by(
        func.count(RawArticle.id).desc()
    ).limit(3).all()

    prompt = f"""أنت مستشار محتوى رقمي خبير. تحلل أداء "غرفة المحتوى" — منصة لإدارة ونشر المحتوى.

بيانات هذا الأسبوع:
- أخبار مسحوبة: {scraped_7d}
- محتوى مُنشأ: {generated_7d}
- منشور فعلياً: {published_7d}
- مرفوض: {rejected_7d}
- معدل النشر: {publish_rate}%
- معدل الرفض: {rejection_rate}%
- المنصات والنشر: {dict(plat_counts)}
- أكثر المصادر نشاطاً: {', '.join([r[0] for r in top_sources])}

أرجع ردك بصيغة JSON فقط (بدون أي نص خارج JSON) بهذا الهيكل الدقيق:
{{
  "summary": "جملتان فقط تلخصان الأداء الأسبوعي",
  "recommendations": [
    {{"title": "عنوان التوصية", "reason": "السبب في جملة واحدة", "priority": "high"}},
    {{"title": "عنوان التوصية", "reason": "السبب في جملة واحدة", "priority": "medium"}},
    {{"title": "عنوان التوصية", "reason": "السبب في جملة واحدة", "priority": "low"}}
  ],
  "warning": {{"text": "تحذير واحد مهم أو فارغ إن لم يوجد", "severity": "high"}},
  "content_idea": {{"title": "فكرة محتوى مبتكرة", "type": "كاروسيل", "why": "لماذا ستنجح"}}
}}

قواعد صارمة: أرجع JSON فقط. لا تضع ```json أو أي نص قبل أو بعد JSON."""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        ai_text = msg.content[0].text.strip() if msg.content else "{}"

        # Parse Claude's JSON response
        try:
            ai_data = json.loads(ai_text)
        except json.JSONDecodeError:
            # Try to extract JSON from text if Claude added extra text
            import re
            match = re.search(r'\{.*\}', ai_text, re.DOTALL)
            ai_data = json.loads(match.group()) if match else {"summary": ai_text}

        return {
            "ai": ai_data,
            "performance": {
                "scraped":        scraped_7d,
                "generated":      generated_7d,
                "published":      published_7d,
                "rejected":       rejected_7d,
                "publish_rate":   publish_rate,
                "rejection_rate": rejection_rate,
            },
            "platforms":   dict(plat_counts),
            "generated_at": now.isoformat()
        }
    except Exception as e:
        return {"error": f"خطأ في الاتصال بـ Claude: {str(e)}"}


@router.post("/content-ideas")
async def get_content_ideas(db: Session = Depends(get_db)):
    """
    Ask Claude to generate 5 content ideas based on recent trending articles.
    """
    import anthropic

    if not settings.ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY غير مُعيَّن"}

    now = datetime.now(timezone.utc)
    last_2d = now - timedelta(days=2)

    recent_articles = db.query(RawArticle).filter(
        RawArticle.created_at >= last_2d
    ).order_by(RawArticle.created_at.desc()).limit(15).all()

    titles = "\n".join([f"- {a.title}" for a in recent_articles if a.title])
    if not titles:
        return {"error": "لا يوجد أخبار حديثة لتوليد أفكار منها"}

    prompt = f"""أنت خبير محتوى سوشيال ميديا. بناءً على الأخبار التالية المسحوبة اليوم:

{titles}

اقترح 5 أفكار محتوى أصلية ومبتكرة مناسبة للنشر على Instagram وLinkedIn.
لكل فكرة:
- عنوان جذاب (جملة واحدة)
- نوع المحتوى (بوست / كاروسيل / فيديو)
- سبب التميز (جملة واحدة)

رد بالعربية فقط. لا تقتبس الأخبار حرفياً — أضف قيمة وزاوية جديدة."""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}]
        )
        ideas_text = msg.content[0].text if msg.content else ""
        return {"ideas": ideas_text, "generated_at": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        return {"error": f"خطأ في Claude: {str(e)}"}
