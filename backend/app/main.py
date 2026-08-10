import sys
import os
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routers import sources, raw_articles, content, stats, templates, social, auth, threads, trends
from app.core.config import settings
from app.core.security import get_current_user
from fastapi import Depends

from contextlib import asynccontextmanager
from app.services.ingestion.scheduler_service import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
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
app.include_router(threads.router, prefix="/api/threads", tags=["Threads API"], dependencies=[Depends(get_current_user)])
app.include_router(trends.router, prefix="/api/trends", tags=["Trends Radar"], dependencies=[Depends(get_current_user)])

@app.get("/api/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

# ── TikTok URL-prefix ownership verification ──────────────────────────────────
from fastapi.responses import PlainTextResponse

@app.get("/tiktokUl3sqscByg3q8nXurtLOC7HXdiExDMDf.txt", response_class=PlainTextResponse, include_in_schema=False)
def tiktok_verification():
    return "tiktok-developers-site-verification=Ul3sqscByg3q8nXurtLOC7HXdiExDMDf"

# Serve frontend HTML/JS/CSS (Must be after API routes)
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
