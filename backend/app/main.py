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

@app.get("/api/health")
def health_check():
    return {
        "status": "ok", 
        "environment": settings.ENVIRONMENT,
        "version": getattr(settings, "VERSION", "v1.0.0"),
        "model": getattr(settings, "CLAUDE_MODEL", "Claude 3.5 Sonnet")
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
