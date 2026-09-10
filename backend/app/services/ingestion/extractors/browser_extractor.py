from typing import List, Dict
from playwright.sync_api import sync_playwright
import trafilatura
from bs4 import BeautifulSoup
import os

def extract_article_content(url: str, html: str) -> Dict:
    try:
        import json
        result = trafilatura.extract(
            html,
            output_format="json",
            include_comments=False,
            include_tables=True,
            include_images=False,
            favor_recall=True,
        )
        content = ''
        title = ''
        published_at = ''
        image_url = ''

        if result:
            data = json.loads(result)
            content = data.get("text", "")
            title = data.get("title", "")
            published_at = data.get("date", "")

        # Always try og:image / JSON-LD from the rendered HTML (more reliable)
        soup = BeautifulSoup(html, "html.parser")

        # JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                ld = json.loads(script.string or '{}')
                items = ld if isinstance(ld, list) else [ld]
                for item in items:
                    img = item.get('image')
                    if isinstance(img, str) and img.startswith('http'):
                        image_url = img; break
                    if isinstance(img, dict):
                        image_url = img.get('url', img.get('contentUrl', '')); break
                    if isinstance(img, list) and img:
                        first = img[0]
                        image_url = first if isinstance(first, str) else first.get('url', ''); break
                if image_url:
                    break
            except Exception:
                pass

        # og:image fallback
        if not image_url:
            for prop in ['og:image', 'twitter:image']:
                tag = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
                if tag and tag.get('content', '').startswith('http'):
                    image_url = tag['content'].strip()
                    break

        if not title:
            og = soup.find('meta', property='og:title')
            if og and og.get('content'):
                title = og['content'].strip()

        return {
            "title": title.strip(),
            "url": url,
            "content": content.strip(),
            "published_at": published_at,
            "image_url": image_url,
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

                    # Strict individual link relevance filter
                    from app.services.ingestion.relevance_filter import is_tech_relevant
                    if not is_tech_relevant(link.get_text(strip=True), ""):
                        print(f"Skipping link (Not tech relevant): {link.get_text(strip=True)}")
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
