from typing import List, Dict
import urllib.robotparser
from urllib.parse import urlparse

from app.services.ingestion.extractors import rss_extractor, generic_extractor, browser_extractor, ai_extractor

def can_fetch(url: str) -> bool:
    try:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        robots_url = f"{base_url}/robots.txt"
        
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch("*", url)
    except Exception as e:
        print(f"Error checking robots.txt for {url}: {e}")
        return True # Default to True if can't read robots.txt

def process_source(url: str) -> List[Dict]:
    """
    Tries layered extraction:
    1. RSS Auto-Discovery
    2. Static HTML (trafilatura)
    3. Headless Browser (Playwright)
    4. AI Extractor
    """
    if not can_fetch(url):
        print(f"Warning: robots.txt forbids crawling for {url}")

    print("Attempting Layer 1: RSS")
    articles = rss_extractor.extract(url)
    if articles:
        return articles
        
    print("Attempting Layer 2: Generic (Static HTML)")
    articles = generic_extractor.extract(url)
    if articles:
        return articles
        
    print("Attempting Layer 3: Headless Browser (Playwright)")
    articles = browser_extractor.extract(url)
    if articles:
        return articles
        
    print("Attempting Layer 4: AI Extractor (Claude)")
    articles = ai_extractor.extract(url)
    if articles:
        return articles
        
    print(f"All layers failed to extract articles from {url}")
    return []
