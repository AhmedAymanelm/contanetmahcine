from typing import List, Dict
from playwright.sync_api import sync_playwright
import trafilatura
from bs4 import BeautifulSoup
import os

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
    articles = []
    # Use system chromium if set via env (Railway/Docker), otherwise let Playwright find its own
    chromium_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    launch_kwargs = {
        "headless": True,
        "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
    }
    if chromium_path:
        launch_kwargs["executable_path"] = chromium_path
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)
            
            try:
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                html = page.content()
                page.close()
            except Exception as e:
                print(f"Error fetching main url {url}: {e}")
                browser.close()
                return []
                
            if not html:
                browser.close()
                return []
                
            soup = BeautifulSoup(html, "html.parser")
            
            for header in soup.find_all(['h2', 'h3']):
                link = header.find('a')
                if link and link.get('href'):
                    href = link.get('href')
                    if not href.startswith('http'):
                        base_url = "/".join(url.split("/")[:3])
                        href = f"{base_url}{href}"
                    
                    if any(a["url"] == href for a in articles):
                        continue
                        
                    try:
                        article_page = browser.new_page()
                        article_page.goto(href, wait_until="networkidle", timeout=30000)
                        article_html = article_page.content()
                        article_page.close()
                    except Exception as e:
                        print(f"Error fetching article url {href}: {e}")
                        continue
                        
                    if not article_html:
                        continue
                        
                    article_data = extract_article_content(href, article_html)
                    
                    if article_data and len(article_data.get("content", "")) > 100:
                        articles.append(article_data)
                    
                    if len(articles) >= 3:
                        break
            
            browser.close()
    except Exception as e:
        print(f"Playwright general error: {e}")
        
    return articles
