from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone
from app.api.deps import SessionLocal
from app.models.source import Source
from app.models.raw_article import RawArticle
from app.services.ingestion.pipeline import process_source
import logging
import asyncio
from app.models.content_item import ContentItem
from app.services.social.instagram import InstagramService
from app.services.social.facebook import FacebookService
from app.services.social.threads_service import ThreadsService
from app.services.social.linkedin_service import LinkedInService
from app.models.oauth_token import OAuthToken

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def check_and_run_ingestion():
    db = SessionLocal()
    try:
        active_sources = db.query(Source).filter(Source.is_active == True).all()
        now = datetime.now(timezone.utc)
        
        for source in active_sources:
            should_scrape = False
            
            if not source.last_scraped_at:
                should_scrape = True
            else:
                last_time = source.last_scraped_at
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                
                diff_mins = (now - last_time).total_seconds() / 60.0
                if diff_mins >= (source.interval_mins or 30):
                    should_scrape = True
                    
            if should_scrape:
                logger.info(f"Auto-Ingestion: Scraping source {source.name}...")
                try:
                    articles = process_source(source.url)
                    total_new = 0
                    for art in articles:
                        exists = db.query(RawArticle).filter(RawArticle.url == art["url"]).first()
                        if not exists:
                            new_art = RawArticle(
                                source_id=source.id,
                                title=art["title"],
                                url=art["url"],
                                content=art["content"],
                                image_url=art.get("image_url"),
                                published_at=None
                            )
                            db.add(new_art)
                            total_new += 1
                    
                    source.last_scraped_at = datetime.utcnow()
                    source.error_count = 0
                    source.health_status = 'ok'
                    db.commit()
                    logger.info(f"Auto-Ingestion: Saved {total_new} new articles for {source.name}")
                except Exception as e:
                    logger.error(f"Auto-Ingestion: Error scraping {source.url}: {e}")
                    source.error_count += 1
                    if source.error_count >= 3:
                        source.health_status = 'needs_review'
                    db.commit()
    finally:
        db.close()

def clear_raw_articles_at_midnight():
    db = SessionLocal()
    try:
        # Delete pending articles only, to avoid breaking links with generated content
        deleted = db.query(RawArticle).filter(RawArticle.status == "PENDING").delete(synchronize_session=False)
        db.commit()
        logger.info(f"Midnight Cleanup: Deleted {deleted} pending raw articles.")
    except Exception as e:
        logger.error(f"Midnight Cleanup Error: {e}")
    finally:
        db.close()

def publish_scheduled_content():
    db = SessionLocal()
    try:
        # Use local time since the frontend sends naive local time to avoid timezone shifts
        now = datetime.now()
        scheduled_items = db.query(ContentItem).filter(
            ContentItem.status == "SCHEDULED",
            ContentItem.scheduled_at <= now
        ).all()
        
        if not scheduled_items:
            return
            
        logger.info(f"Found {len(scheduled_items)} scheduled items to publish.")
        
        async def publish_item(item):
            platforms = item.platforms or []
            if isinstance(platforms, str):
                platforms = platforms.split(",")
            is_ig = any("IG" in p.upper() or "INSTAGRAM" in p.upper() for p in platforms)
            is_fb = any("FB" in str(p).upper() or "FACEBOOK" in str(p).upper() for p in platforms)
            is_th = any("TH" in str(p).upper() or "THREADS" in str(p).upper() for p in platforms)
            is_li = any("LI" in str(p).upper() or "LINKEDIN" in str(p).upper() for p in platforms)
            
            ig_published = False
            if is_ig and item.generated_content:
                ig_service = InstagramService()
                if ig_service._is_configured():
                    gen = item.generated_content
                    caption = gen.get("instagram_caption", gen.get("title", ""))
                    
                    if item.content_type == "CAROUSEL" and "carousel_urls" in gen:
                        urls = gen["carousel_urls"]
                        if urls:
                            res = await ig_service.publish_carousel(urls, caption)
                            if res.get("success"):
                                ig_published = True
                            else:
                                logger.error(f"IG Scheduled publish failed for item {item.id}: {res}")
                    elif item.content_type == "POST" and "image_url" in gen:
                        res = await ig_service.publish_image(gen["image_url"], caption)
                        if res.get("success"):
                            ig_published = True
                        else:
                            logger.error(f"IG Scheduled publish failed for item {item.id}: {res}")

            fb_published = False
            if is_fb and item.generated_content:
                fb_service = FacebookService()
                if fb_service._is_configured():
                    gen = item.generated_content
                    caption = gen.get("facebook_post", gen.get("title", ""))
                    
                    if item.content_type == "CAROUSEL" and "carousel_urls" in gen:
                        urls = gen["carousel_urls"]
                        if urls:
                            res = await fb_service.publish_carousel(urls, caption)
                            if res.get("success"):
                                fb_published = True
                            else:
                                logger.error(f"FB Scheduled publish failed for item {item.id}: {res}")
                    elif item.content_type == "POST":
                        if "image_url" in gen and gen["image_url"]:
                            res = await fb_service.publish_image(gen["image_url"], caption)
                        else:
                            res = await fb_service.publish_text(caption)
                            
                        if res.get("success"):
                            fb_published = True
                        else:
                            logger.error(f"FB Scheduled publish failed for item {item.id}: {res}")

            th_published = False
            if is_th and item.generated_content:
                th_service = ThreadsService()
                status = th_service.get_status(db)
                if status.get("connected"):
                    gen = item.generated_content
                    caption = gen.get("x_tweet", gen.get("instagram_caption", gen.get("title", "")))
                    
                    if len(caption) > 500:
                        caption = caption[:497] + "..."
                        
                    access_token = await th_service.check_and_refresh_token(db)
                    if access_token and status.get("account_id"):
                        res = await th_service.publish_text(caption, access_token, status.get("account_id"))
                        if res.get("success"):
                            th_published = True
                        else:
                            logger.error(f"Threads Scheduled publish failed for item {item.id}: {res}")

            li_published = False
            if is_li and item.generated_content:
                li_service = LinkedInService()
                status = li_service.get_status(db)
                if status.get("connected"):
                    gen = item.generated_content
                    caption = gen.get("linkedin_post", gen.get("title", ""))
                    
                    access_token = token_entry.access_token if (token_entry := db.query(OAuthToken).filter(OAuthToken.platform == "linkedin").first()) else None
                    if access_token and status.get("account_id"):
                        res = await li_service.publish_text(caption, access_token, status.get("account_id"))
                        if res.get("success"):
                            li_published = True
                        else:
                            logger.error(f"LinkedIn Scheduled publish failed for item {item.id}: {res}")

            if ig_published or fb_published or th_published or li_published:
                return True
            elif not is_ig and not is_fb and not is_th and not is_li:
                # If neither IG nor FB nor TH nor LI are selected, just mark published (e.g. mock publishing)
                return True
            return False
            
        for item in scheduled_items:
            try:
                success = asyncio.run(publish_item(item))
                if success:
                    item.status = "PUBLISHED"
                    item.published_at = datetime.now(timezone.utc)
                    db.commit()
                    logger.info(f"Successfully published scheduled item {item.id}")
                else:
                    logger.error(f"Failed to publish scheduled item {item.id}")
            except Exception as e:
                logger.error(f"Error publishing scheduled item {item.id}: {e}")
                
    except Exception as e:
        logger.error(f"Scheduler Publishing Error: {e}")
    finally:
        db.close()

def auto_scrape_trend_radar():
    """
    Background job to automatically fetch the top trending tech/crypto news
    from Google News and AITnews every 2 hours and save them as RawArticles.
    """
    db = SessionLocal()
    try:
        source = db.query(Source).filter(Source.name == "Trend Radar (Auto Pilot)").first()
        if not source:
            source = Source(
                name="Trend Radar (Auto Pilot)",
                url="https://news.google.com/rss/",
                scraping_type="RSS",
                interval_mins=120,
                is_active=True
            )
            db.add(source)
            db.commit()
            db.refresh(source)
            
        from app.api.routers.trends import fetch_trends_for_geo
        import trafilatura
        import json
        from googlenewsdecoder import new_decoderv1
        from bs4 import BeautifulSoup
        
        geos = ["AITNEWS", "GLOBAL"]
        total_new = 0
        
        for geo in geos:
            logger.info(f"Auto-Trend: Fetching trends for {geo}")
            try:
                trends = fetch_trends_for_geo(geo)
                for trend in trends:
                    # Check if already in DB
                    exists = db.query(RawArticle).filter(RawArticle.url == trend.news_url).first()
                    if exists:
                        continue
                        
                    # Scrape content
                    try:
                        decoded_res = new_decoderv1(trend.news_url)
                        real_url = decoded_res.get('decoded_url') if decoded_res.get('status') else trend.news_url
                        
                        downloaded = trafilatura.fetch_url(real_url)
                        if not downloaded:
                            continue
                            
                        result = trafilatura.extract(downloaded, output_format="json", include_comments=False, include_tables=False, include_images=True)
                        if not result:
                            continue
                            
                        data = json.loads(result)
                        content = data.get("text", "")
                        image_url = data.get("image", "")
                        
                        if not image_url:
                            try:
                                soup = BeautifulSoup(downloaded, "html.parser")
                                meta_img = soup.find("meta", property="og:image")
                                if meta_img and meta_img.get("content"):
                                    image_url = meta_img["content"]
                            except Exception:
                                pass
                                
                        if len(content) > 100:
                            new_art = RawArticle(
                                source_id=source.id,
                                title=trend.title,
                                url=trend.news_url,
                                content=content,
                                image_url=image_url,
                                published_at=None
                            )
                            db.add(new_art)
                            db.commit()
                            total_new += 1
                    except Exception as scrape_err:
                        logger.error(f"Auto-Trend: Error scraping {trend.news_url}: {scrape_err}")
            except Exception as geo_err:
                logger.error(f"Auto-Trend: Error fetching trends for {geo}: {geo_err}")
                
        logger.info(f"Auto-Trend: Saved {total_new} new trend articles.")
    except Exception as e:
        logger.error(f"Auto-Trend: Critical error: {e}")
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        # Run every 5 minutes to check schedules
        scheduler.add_job(
            check_and_run_ingestion, 
            trigger=IntervalTrigger(minutes=5),
            id='auto_ingestion_job',
            name='Auto Ingestion Job',
            replace_existing=True
        )
        
        # Run exactly at midnight every day
        scheduler.add_job(
            clear_raw_articles_at_midnight,
            trigger=CronTrigger(hour=0, minute=0),
            id='midnight_cleanup_job',
            name='Midnight Cleanup Job',
            replace_existing=True
        )
        
        # Run every 1 minute to check for scheduled posts
        scheduler.add_job(
            publish_scheduled_content,
            trigger=IntervalTrigger(minutes=1),
            id='publish_scheduled_job',
            name='Publish Scheduled Job',
            replace_existing=True
        )
        
        # Run every 2 hours to auto-scrape trend radar
        scheduler.add_job(
            auto_scrape_trend_radar,
            trigger=IntervalTrigger(hours=2),
            id='auto_scrape_trend_radar_job',
            name='Auto Scrape Trend Radar Job',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Background Auto-Ingestion Scheduler started.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background Auto-Ingestion Scheduler stopped.")
