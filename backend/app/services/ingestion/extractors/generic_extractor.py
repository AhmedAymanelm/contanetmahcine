import httpx
from typing import List, Dict
import trafilatura
from bs4 import BeautifulSoup
from app.core.config import settings

def extract_article_content(url: str) -> Dict:
    try:
        response = httpx.get(url, timeout=settings.REQUEST_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
        downloaded = response.text
        if not downloaded:
            return {}
            
        result = trafilatura.extract(
            downloaded,
            output_format="json",
            include_comments=False,
            include_tables=False,
            include_images=True,
            include_links=False
        )
        
        if result:
            import json
            data = json.loads(result)
            image_url = data.get("image", "")
            title = data.get("title", "")
            
            # Fallback to BeautifulSoup if trafilatura missed metadata
            if downloaded:
                soup = BeautifulSoup(downloaded, "html.parser")
                if not image_url:
                    og_img = soup.find("meta", property="og:image")
                    if og_img and og_img.get("content"):
                        image_url = og_img.get("content")
                if not title:
                    og_title = soup.find("meta", property="og:title")
                    if og_title and og_title.get("content"):
                        title = og_title.get("content")
                    elif soup.title:
                        title = soup.title.string

            return {
                "title": title.strip() if title else "",
                "url": url,
                "content": data.get("text", ""),
                "published_at": data.get("date", ""),
                "image_url": image_url
            }
    except Exception as e:
        print(f"Error in Generic Extractor for {url}: {e}")
    return {}

def extract(url: str) -> List[Dict]:
    # Extract links from homepage, then extract content from each link
    try:
        response = httpx.get(url, timeout=settings.REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        articles = []
        # Find all <a> tags that contain enough text to be a news title
        for link in soup.find_all('a'):
            href = link.get('href')
            text = link.get_text(strip=True)
            
            # A typical Arabic news title is at least 25 characters long
            if href and len(text) > 25:
                if not href.startswith('http'):
                    base_url = "/".join(url.split("/")[:3])
                    href = f"{base_url}{href}"
                
                # Deduplicate
                if any(a["url"] == href for a in articles):
                    continue
                    
                article_data = extract_article_content(href)
                # Quality check: title and content must be substantial
                if article_data and len(article_data.get("content", "")) > 100:
                    articles.append(article_data)
                
                if len(articles) >= 5: # Limit for performance during testing
                    break
                    
        return articles
    except Exception as e:
        print(f"Error scraping links from {url}: {e}")
        return []
