import feedparser
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import httpx
from app.core.config import settings

def _is_valid_rss(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=settings.REQUEST_TIMEOUT)
        return "xml" in response.headers.get("Content-Type", "") or "rss" in response.text.lower()[:500]
    except Exception:
        return False

def discover_rss(url: str) -> Optional[str]:
    # 1. Try directly if it's already an RSS feed
    if _is_valid_rss(url):
        return url
        
    try:
        response = httpx.get(url, timeout=settings.REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        # 2. Check <link rel="alternate" type="application/rss+xml">
        link = soup.find('link', type='application/rss+xml')
        if link and link.get('href'):
            href = link.get('href')
            if not href.startswith('http'):
                base_url = "/".join(url.split("/")[:3])
                href = f"{base_url}{href}"
            if _is_valid_rss(href):
                return href
                
        # 3. Try common suffixes
        base_url = url.rstrip("/")
        for suffix in ["/feed", "/rss", "/rss.xml"]:
            test_url = f"{base_url}{suffix}"
            if _is_valid_rss(test_url):
                return test_url
    except Exception as e:
        print(f"Error in RSS auto-discovery for {url}: {e}")
        
    return None

def extract(url: str) -> List[Dict]:
    rss_url = discover_rss(url)
    if not rss_url:
        return []
        
    try:
        parsed_feed = feedparser.parse(rss_url)
        articles = []
        for entry in parsed_feed.entries[:10]:
            articles.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "content": entry.get("summary", ""),
                "published_at": entry.get("published", "")
            })
        return articles
    except Exception as e:
        print(f"Error parsing RSS {rss_url}: {e}")
        return []
