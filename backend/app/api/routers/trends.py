from fastapi import APIRouter, Depends, BackgroundTasks
import feedparser
import httpx
from typing import List, Optional
from pydantic import BaseModel
import re

from app.api.deps import get_db
from app.services.generation.runner import process_trend_generation

router = APIRouter()

class TrendItem(BaseModel):
    title: str
    traffic: str
    description: str
    pub_date: str
    news_title: str
    news_url: str
    news_snippet: str

class TrendGenerateRequest(BaseModel):
    title: str
    snippet: str

@router.get("/", response_model=List[TrendItem])
def get_trends(geo: str = "EG"):
    """
    Fetches real-time technology news from Google News for a specific country.
    """
    import urllib.parse
    
    # Niche topics specifically for a tech/finance/crypto content creator
    query = 'الذكاء الاصطناعي OR بيتكوين OR انفيديا OR مايكروسوفت OR جوجل OR OpenAI OR عملات رقمية OR تداول OR آبل OR ايلون ماسك'
    encoded_query = urllib.parse.quote(query)
    
    if geo == "GLOBAL":
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ar&gl=AE&ceid=AE:ar"
    else:
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ar&gl={geo}&ceid={geo}:ar"
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Fetch using httpx to bypass basic blocks
    response = httpx.get(url, headers=headers, follow_redirects=True)
    
    if response.status_code != 200:
        return []

    feed = feedparser.parse(response.text)
    
    trends = []
    for entry in feed.entries[:15]:  # Limit to top 15 tech news
        # Google News RSS puts source inside 'source' tag
        source_name = ""
        if hasattr(entry, 'source') and hasattr(entry.source, 'title'):
            source_name = entry.source.title
            
        trends.append(TrendItem(
            title=entry.title,
            traffic=source_name, # Use traffic field to show the news source
            description="أخبار تكنولوجية عاجلة",
            pub_date=entry.get("published", ""),
            news_title=entry.title,
            news_url=entry.link,
            news_snippet=entry.title
        ))
        
    return trends

@router.post("/generate")
def generate_trend_content(request: TrendGenerateRequest, background_tasks: BackgroundTasks):
    """
    Triggers background generation of content based on a Trend.
    """
    background_tasks.add_task(process_trend_generation, request.title, request.snippet)
    return {"detail": "Trend content generation started in the background"}
