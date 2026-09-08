from cloudinary.api import delete_derived_resources
import sys
import os
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routers import sources, raw_articles, content, stats, templates, social, auth, threads, trends, settings as settings_router_module
from app.api.routers.analytics import router as analytics_router
from app.api.routers.recommendations import router as recommendations_router
from app.core.config import settings
from app.core.security import get_current_user
from fastapi import Depends

from contextlib import asynccontextmanager
from app.services.ingestion.scheduler_service import start_scheduler, stop_scheduler
from app.db.session import SessionLocal
from app.models.app_setting import AppSetting

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load dynamic settings from database
    try:
        db = SessionLocal()
        db_settings = db.query(AppSetting).all()
        for s in db_settings:
            if hasattr(settings, s.key):
                if s.value.lower() == "true":
                    setattr(settings, s.key, True)
                elif s.value.lower() == "false":
                    setattr(settings, s.key, False)
                else:
                    setattr(settings, s.key, s.value)
        db.close()
    except Exception as e:
        print(f"Failed to load DB settings on startup: {e}")

    # Auto-reset any articles stuck in APPROVED_FOR_GENERATION (killed by previous restart)
    try:
        from app.models.raw_article import RawArticle
        db = SessionLocal()
        stuck = db.query(RawArticle).filter(RawArticle.status == "APPROVED_FOR_GENERATION").all()
        if stuck:
            for art in stuck:
                art.status = "PENDING"
            db.commit()
            print(f"[Startup] Reset {len(stuck)} stuck article(s) back to PENDING")
        db.close()
    except Exception as e:
        print(f"[Startup] Failed to reset stuck articles: {e}")

    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Serve static files (carousel output images)
STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")




# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(sources.router, prefix="/api/sources", tags=["Sources"], dependencies=[Depends(get_current_user)])
app.include_router(raw_articles.router, prefix="/api/raw-articles", tags=["Raw Articles"], dependencies=[Depends(get_current_user)])
app.include_router(content.router, prefix="/api/content", tags=["Content Items"], dependencies=[Depends(get_current_user)])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"], dependencies=[Depends(get_current_user)])
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"], dependencies=[Depends(get_current_user)])
app.include_router(social.router, prefix="/api/social", tags=["Social Integration"], dependencies=[Depends(get_current_user)])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"]) # Move to /api/auth
app.include_router(auth.router, prefix="/auth", tags=["Authentication Legacy"]) # For old redirect URIs
app.include_router(threads.router, prefix="/api/threads", tags=["Threads API"], dependencies=[Depends(get_current_user)])
app.include_router(trends.router, prefix="/api/trends", tags=["Trends Radar"], dependencies=[Depends(get_current_user)])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"], dependencies=[Depends(get_current_user)])
app.include_router(recommendations_router, prefix="/api/recommendations", tags=["Recommendations"], dependencies=[Depends(get_current_user)])
app.include_router(settings_router_module.router, prefix="/api/settings", tags=["Settings"], dependencies=[Depends(get_current_user)])

# ── Image Proxy (no auth needed — used by img tags in browser) ─────────────
from fastapi import Query
from fastapi.responses import Response as FastAPIResponse
import httpx as _httpx
from urllib.parse import urlparse as _urlparse

@app.get("/api/img-proxy")
async def image_proxy(url: str = Query(..., description="Image URL to proxy")):
    """Proxy external images to bypass hotlink protection."""
    try:
        parsed = _urlparse(url)
        if not parsed.scheme.startswith('http'):
            return FastAPIResponse(status_code=400, content=b"")
        referer = f"{parsed.scheme}://{parsed.netloc}/"
        async with _httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            resp = await client.get(url, headers={
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/124.0.0.0 Safari/537.36"),
                "Referer": referer,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            })
        if resp.status_code == 200:
            ct = resp.headers.get("content-type", "image/jpeg")
            return FastAPIResponse(content=resp.content, media_type=ct,
                                   headers={"Cache-Control": "public, max-age=86400"})
        return FastAPIResponse(status_code=resp.status_code, content=b"")
    except Exception:
        return FastAPIResponse(status_code=502, content=b"")

@app.get("/api/health")
def health_check():
    import os
    model = os.environ.get("DEFAULT_MODEL", "claude-sonnet-4-5 (default fallback)")
    key_preview = settings.ANTHROPIC_API_KEY[:12] + "..." if settings.ANTHROPIC_API_KEY else "NOT SET"
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "version": getattr(settings, "VERSION", "v1.0.0"),
        "model": model,
        "api_key_preview": key_preview
    }

@app.get("/api/test-ai")
def test_ai():
    """Test Anthropic API key and model configuration."""
    import os
    import anthropic
    key = settings.ANTHROPIC_API_KEY
    model = os.environ.get("DEFAULT_MODEL", "claude-sonnet-4-5")
    if not key:
        return {"status": "error", "error": "ANTHROPIC_API_KEY is not set"}
    try:
        client = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Say: OK"}]
        )
        return {
            "status": "success",
            "model_used": model,
            "key_preview": key[:12] + "...",
            "response": response.content[0].text
        }
    except Exception as e:
        return {
            "status": "error",
            "model_used": model,
            "key_preview": key[:12] + "...",
            "error": str(e)
        }

# ── TikTok URL-prefix ownership verification ──────────────────────────────────
from fastapi.responses import PlainTextResponse, FileResponse

TIKTOK_VERIFICATION_FILE = Path(__file__).parent.parent.parent / "tiktokSJ8XSVAnAVL4ewXcnsFkyzq47euAuVgp.txt"

@app.get("/tiktokSJ8XSVAnAVL4ewXcnsFkyzq47euAuVgp.txt", response_class=PlainTextResponse, include_in_schema=False)
def tiktok_verification():
    if TIKTOK_VERIFICATION_FILE.exists():
        return TIKTOK_VERIFICATION_FILE.read_text(encoding="utf-8").strip()
    return "tiktok-developers-site-verification=SJ8XSVAnAVL4ewXcnsFkyzq47euAuVgp"

# ── Legal pages ───────────────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"


@app.get("/terms", response_class=FileResponse, include_in_schema=False)
def terms_page():
    return FileResponse(str(FRONTEND_DIR / "terms.html"), media_type="text/html")

@app.get("/privacy", response_class=FileResponse, include_in_schema=False)
def privacy_page():
    return FileResponse(str(FRONTEND_DIR / "privacy.html"), media_type="text/html")

# Serve frontend HTML/JS/CSS (Must be after API routes)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
