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
    Fetches real-time daily search trends from Google Trends for a specific country.
    Available Geos: EG (Egypt), SA (Saudi Arabia), AE (UAE), US, etc.
    """
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Fetch using httpx to bypass basic blocks
    response = httpx.get(url, headers=headers)
    
    if response.status_code != 200:
        return []

    feed = feedparser.parse(response.content)
    
    trends = []
    for entry in feed.entries:
        # Extract traffic (e.g. "50K+")
        traffic = entry.get("ht_approx_traffic", "")
        
        # Extract related news
        news_title = ""
        news_url = ""
        news_snippet = ""
        
        # Google Trends RSS puts news inside ht_news_item
        if hasattr(entry, "ht_news_item"):
            news_item = entry.ht_news_item
            if isinstance(news_item, dict):
                news_title = news_item.get("ht_news_item_title", "")
                news_url = news_item.get("ht_news_item_url", "")
                news_snippet = news_item.get("ht_news_item_snippet", "")
            elif hasattr(entry, 'ht_news_item_title'):
                news_title = entry.get("ht_news_item_title", "")
                news_snippet = entry.get("ht_news_item_snippet", "")
                news_url = entry.get("ht_news_item_url", "")
            elif isinstance(news_item, str):
                news_snippet = news_item
                
        # Fallback to standard description if snippet is empty
        description = entry.get("description", "")
        
        # Clean HTML from snippets
        clean_snippet = re.sub(r'<[^>]+>', '', news_snippet) if news_snippet else ""
        clean_desc = re.sub(r'<[^>]+>', '', description) if description else ""
        
        trends.append(TrendItem(
            title=entry.title,
            traffic=traffic,
            description=clean_desc,
            pub_date=entry.get("published", ""),
            news_title=news_title,
            news_url=news_url,
            news_snippet=clean_snippet or clean_desc
        ))
        
    return trends

@router.post("/generate")
def generate_trend_content(request: TrendGenerateRequest, background_tasks: BackgroundTasks):
    """
    Triggers background generation of content based on a Trend.
    """
    background_tasks.add_task(process_trend_generation, request.title, request.snippet)
    return {"detail": "Trend content generation started in the background"}
