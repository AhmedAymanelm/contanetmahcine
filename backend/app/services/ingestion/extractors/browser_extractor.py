from typing import List, Dict
from playwright.sync_api import sync_playwright
import trafilatura
from bs4 import BeautifulSoup

def _get_page_html(url: str) -> str:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page()
            # Wait until network is idle to ensure JS has rendered
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"Error in Playwright for {url}: {e}")
        return ""

def extract_article_content(url: str, html: str) -> Dict:
    try:
        result = trafilatura.extract(
            html,
            output_format="json",
            include_comments=False,
            include_tables=False,
            include_images=True
        )
        if result:
            import json
            data = json.loads(result)
            return {
                "title": data.get("title", ""),
                "url": url,
                "content": data.get("text", ""),
                "published_at": data.get("date", ""),
                "image_url": data.get("image", "")
            }
    except Exception as e:
        print(f"Error in Browser Content Extractor for {url}: {e}")
    return {}

def extract(url: str) -> List[Dict]:
    html = _get_page_html(url)
    if not html:
        return []
        
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    
    for header in soup.find_all(['h2', 'h3']):
        link = header.find('a')
        if link and link.get('href'):
            href = link.get('href')
            if not href.startswith('http'):
                base_url = "/".join(url.split("/")[:3])
                href = f"{base_url}{href}"
            
            if any(a["url"] == href for a in articles):
                continue
                
            article_html = _get_page_html(href)
            if not article_html:
                continue
                
            article_data = extract_article_content(href, article_html)
            
            # Quality check
            if article_data and len(article_data.get("content", "")) > 100:
                articles.append(article_data)
                
            if len(articles) >= 3: # Browser is slow, limit to 3
                break
                
    return articles
