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

def fetch_trends_for_geo(geo: str) -> List[TrendItem]:
    """
    Core function to fetch trends for a specific geo so it can be called by both API and background workers.
    """
    import feedparser
    import httpx
    import urllib.parse
    
    # Niche topics specifically for a tech/finance/crypto content creator
    # Added when:2d to restrict results to the last 48 hours
    query = '(الذكاء الاصطناعي OR بيتكوين OR انفيديا OR مايكروسوفت OR جوجل OR OpenAI OR عملات رقمية OR تداول OR آبل OR ايلون ماسك) when:2d'
    encoded_query = urllib.parse.quote(query)
    
    if geo == "AITNEWS":
        url = "https://aitnews.com/feed/"
    elif geo == "GLOBAL":
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
    for entry in feed.entries[:15]:  # Limit to top 15 news
        # Handle source name for Google News vs AITnews
        if geo == "AITNEWS":
            source_name = "البوابة العربية للأخبار التقنية"
        else:
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

@router.get("/", response_model=List[TrendItem])
def get_trends(geo: str = "EG"):
    """
    Fetches real-time technology news from Google News for a specific country.
    """
    return fetch_trends_for_geo(geo)

class ReadRequest(BaseModel):
    url: str

@router.post("/read")
def read_news_article(req: ReadRequest):
    """Scrape the actual news article behind the Google News obfuscated URL"""
    import trafilatura
    import json
    from googlenewsdecoder import new_decoderv1
    
    try:
        # Decode the obfuscated Google News URL natively
        decoded_res = new_decoderv1(req.url)
        real_url = decoded_res.get('decoded_url') if decoded_res.get('status') else req.url
        
        # Download and extract the article
        downloaded = trafilatura.fetch_url(real_url)
        if not downloaded:
            return {"title": "خطأ", "content": "تعذر الاتصال بموقع الخبر الأصلي.", "image": ""}
            
        result = trafilatura.extract(
            downloaded,
            output_format="json",
            include_comments=False,
            include_tables=False,
            include_images=True
        )
        if not result:
             return {"title": "خطأ", "content": "حدث خطأ أثناء استخراج النص من المقال. قد يكون الموقع محمياً ضد السحب الآلي.", "image": ""}
             
        data = json.loads(result)
        image_url = data.get("image", "")
        
        # Fallback for image extraction
        if not image_url:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(downloaded, "html.parser")
                meta_img = soup.find("meta", property="og:image")
                if meta_img and meta_img.get("content"):
                    image_url = meta_img["content"]
            except Exception:
                pass
                
        return {
            "title": data.get("title", ""),
            "content": data.get("text", ""),
            "image": image_url
        }
    except Exception as e:
        print(f"Error reading news: {e}")
        return {"title": "خطأ", "content": "تعذر فتح الرابط الأصلي للخبر.", "image": ""}

@router.post("/generate")
def generate_trend_content(request: TrendGenerateRequest, background_tasks: BackgroundTasks):
    """
    Triggers background generation of content based on a Trend.
    """
    background_tasks.add_task(process_trend_generation, request.title, request.snippet)
    return {"detail": "Trend content generation started in the background"}
