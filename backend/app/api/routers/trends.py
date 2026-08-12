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
    formats: List[str] = ["POST", "CAROUSEL", "VIDEO_SCRIPT"]

def fetch_trends_for_geo(geo: str) -> List[TrendItem]:
    """
    Fetch actual Google Trends for the specified country.
    """
    import httpx
    import xml.etree.ElementTree as ET
    
    # Map 'GLOBAL' to 'US' or 'WW' if possible, but Trends Daily RSS requires a specific country.
    # We will use US for GLOBAL as a fallback.
    country_code = geo if geo != "GLOBAL" else "US"
    if country_code == "AITNEWS":
        country_code = "EG" # Fallback
        
    url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={country_code}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    response = httpx.get(url, headers=headers, follow_redirects=True, timeout=10.0)
    
    if response.status_code != 200:
        return []

    trends = []
    try:
        root = ET.fromstring(response.content)
        channel = root.find("channel")
        if not channel:
            return []
            
        # Namespaces used in Google Trends RSS
        ns = {"ht": "https://trends.google.com/trends/trendingsearches/daily"}
        
        for item in channel.findall("item")[:15]:
            title = item.findtext("title") or "بدون عنوان"
            traffic = item.findtext("ht:approx_traffic", namespaces=ns) or "10K+"
            pub_date = item.findtext("pubDate") or ""
            
            # Fetch the first news item if available
            news_item = item.find("ht:news_item", namespaces=ns)
            news_title = title
            news_url = ""
            news_snippet = title
            source_name = "بحث جوجل"
            
            if news_item is not None:
                news_title = news_item.findtext("ht:news_item_title", namespaces=ns) or title
                news_url = news_item.findtext("ht:news_item_url", namespaces=ns) or ""
                news_snippet = news_item.findtext("ht:news_item_snippet", namespaces=ns) or title
                source_name = news_item.findtext("ht:news_item_source", namespaces=ns) or "أخبار"
                
            trends.append(TrendItem(
                title=title,
                traffic=f"عمليات بحث: {traffic} - {source_name}",
                description=news_snippet,
                pub_date=pub_date,
                news_title=news_title,
                news_url=news_url,
                news_snippet=news_snippet
            ))
    except Exception as e:
        print(f"Error parsing trends XML: {e}")
        
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
    background_tasks.add_task(process_trend_generation, request.title, request.snippet, request.formats)
    return {"message": "Generation started in background"}
