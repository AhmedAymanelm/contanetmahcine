import feedparser
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import httpx
import json
from app.core.config import settings

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _is_valid_rss(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=settings.REQUEST_TIMEOUT, headers=HEADERS, follow_redirects=True)
        ct = response.headers.get("Content-Type", "")
        return ("xml" in ct or "rss" in ct or "atom" in ct or
                "rss" in response.text.lower()[:500] or
                "<feed" in response.text.lower()[:500])
    except Exception:
        return False

def discover_rss(url: str) -> Optional[str]:
    if _is_valid_rss(url):
        return url
    try:
        response = httpx.get(url, timeout=settings.REQUEST_TIMEOUT, headers=HEADERS, follow_redirects=True)
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all('link', type=lambda t: t and ('rss' in t or 'atom' in t)):
            href = link.get('href', '')
            if not href:
                continue
            if not href.startswith('http'):
                base_url = "/".join(url.split("/")[:3])
                href = f"{base_url}{href}"
            if _is_valid_rss(href):
                return href
        base_url = url.rstrip("/")
        for suffix in ["/feed", "/rss", "/rss.xml", "/atom.xml", "/feed/rss", "/?feed=rss2"]:
            test_url = f"{base_url}{suffix}"
            if _is_valid_rss(test_url):
                return test_url
    except Exception as e:
        print(f"Error in RSS auto-discovery for {url}: {e}")
    return None

def _extract_image_from_entry(entry) -> str:
    """Try multiple RSS image fields."""
    # 1. media:content
    if hasattr(entry, 'media_content') and entry.media_content:
        for m in entry.media_content:
            url = m.get('url', '')
            if url and not url.endswith('.gif'):
                return url
    # 2. media:thumbnail
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        url = entry.media_thumbnail[0].get('url', '')
        if url:
            return url
    # 3. enclosure
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image'):
                return enc.get('href', enc.get('url', ''))
    # 4. Parse summary/content HTML for <img>
    for field in ['summary', 'content']:
        raw = ''
        if field == 'content' and hasattr(entry, 'content') and entry.content:
            raw = entry.content[0].get('value', '')
        elif field == 'summary':
            raw = entry.get('summary', '')
        if raw:
            soup = BeautifulSoup(raw, 'html.parser')
            img = soup.find('img')
            if img:
                src = img.get('src') or img.get('data-src', '')
                if src and src.startswith('http') and not src.endswith('.gif'):
                    return src
    return ''

def _fetch_article_content_and_image(article_url: str):
    """Fetch the article page to get full content + image via og:image."""
    try:
        import trafilatura
        resp = httpx.get(article_url, timeout=settings.REQUEST_TIMEOUT, headers=HEADERS, follow_redirects=True)
        html = resp.text
        # Get image from og:image
        soup = BeautifulSoup(html, 'html.parser')
        image_url = ''
        for meta_prop in ['og:image', 'twitter:image']:
            tag = soup.find('meta', property=meta_prop) or soup.find('meta', attrs={'name': meta_prop})
            if tag and tag.get('content'):
                image_url = tag['content']
                break

        # Get full content via trafilatura
        result = trafilatura.extract(
            html,
            output_format='json',
            include_comments=False,
            include_tables=True,
            include_images=False,
            include_links=False,
            favor_recall=True,
            no_fallback=False,
        )
        content = ''
        if result:
            data = json.loads(result)
            content = data.get('text', '')
        return content, image_url
    except Exception as e:
        print(f"Error fetching full article {article_url}: {e}")
        return '', ''

def extract(url: str) -> List[Dict]:
    rss_url = discover_rss(url)
    if not rss_url:
        return []
    try:
        parsed_feed = feedparser.parse(rss_url)
        articles = []
        for entry in parsed_feed.entries[:15]:
            title   = entry.get('title', '').strip()
            link    = entry.get('link', '').strip()
            summary = entry.get('summary', '')
            published = entry.get('published', '')

            if not title or not link:
                continue

            # Clean summary HTML
            soup = BeautifulSoup(summary, 'html.parser')
            clean_summary = soup.get_text(separator=' ', strip=True)

            image_url = _extract_image_from_entry(entry)
            full_content = clean_summary

            # Fetch full article page if:
            # - summary is short (need more content), OR
            # - no image found in RSS (always try to get og:image from the page)
            needs_content = len(clean_summary) < 400
            needs_image   = not image_url

            if needs_content or needs_image:
                fetched_content, fetched_image = _fetch_article_content_and_image(link)
                if needs_content and fetched_content and len(fetched_content) > len(clean_summary):
                    full_content = fetched_content
                if needs_image and fetched_image:
                    image_url = fetched_image

            if not full_content or len(full_content) < 50:
                continue

            articles.append({
                'title': title,
                'url': link,
                'content': full_content,
                'published_at': published,
                'image_url': image_url,
            })

        print(f"RSS extracted {len(articles)} articles from {rss_url}")
        return articles
    except Exception as e:
        print(f"Error parsing RSS {rss_url}: {e}")
        return []
