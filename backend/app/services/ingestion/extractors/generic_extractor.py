import httpx
import json
from typing import List, Dict
import trafilatura
from bs4 import BeautifulSoup
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

def _get_image_from_html(soup: BeautifulSoup, base_url: str) -> str:
    """Extract best image from HTML: og:image > twitter:image > first large img."""
    # 1. og:image
    for prop in ['og:image', 'twitter:image']:
        tag = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
        if tag and tag.get('content'):
            img = tag['content'].strip()
            if img.startswith('http'):
                return img

    # 2. Scan img tags with lazy-load support
    for img in soup.find_all(['img', 'source']):
        src = (img.get('src') or img.get('data-src') or
               img.get('data-lazy-src') or img.get('data-original') or
               img.get('data-lazy') or '')
        if not src:
            srcset = img.get('srcset', '')
            if srcset:
                src = srcset.split(',')[-1].strip().split(' ')[0]
        if not src or src.startswith('data:') or src.endswith('.gif') or src.endswith('.svg'):
            continue
        w = img.get('width', '')
        h = img.get('height', '')
        if w and str(w).isdigit() and int(w) < 150:
            continue
        if h and str(h).isdigit() and int(h) < 150:
            continue
        # Build absolute URL
        if src.startswith('//'):
            src = 'https:' + src
        elif src.startswith('/'):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            src = f"{parsed.scheme}://{parsed.netloc}{src}"
        if src.startswith('http'):
            return src
    return ''


def extract_article_content(url: str) -> Dict:
    try:
        response = httpx.get(
            url, timeout=settings.REQUEST_TIMEOUT,
            follow_redirects=True, headers=HEADERS
        )
        response.raise_for_status()
        downloaded = response.text
        if not downloaded:
            return {}

        soup = BeautifulSoup(downloaded, 'html.parser')

        # Run trafilatura with recall-favoring settings for Arabic sites
        result = trafilatura.extract(
            downloaded,
            output_format='json',
            include_comments=False,
            include_tables=True,
            include_images=False,
            include_links=False,
            favor_recall=True,     # Get MORE text even if less precise
            no_fallback=False,     # Use fallback extractors
            deduplicate=True,
        )

        content = ''
        title = ''
        published_at = ''
        image_url = ''

        if result:
            data = json.loads(result)
            content = data.get('text', '')
            title = data.get('title', '')
            published_at = data.get('date', '')
            image_url = data.get('image', '')

        # Fallback: BeautifulSoup for metadata if trafilatura missed it
        if not image_url:
            image_url = _get_image_from_html(soup, url)

        if not title:
            og = soup.find('meta', property='og:title')
            if og and og.get('content'):
                title = og['content'].strip()
            elif soup.title:
                title = soup.title.string or ''
                title = title.strip()

        # If trafilatura gave very little content, try BS4 article body
        if len(content) < 300:
            for sel in ['article', '[class*="article-body"]', '[class*="post-content"]',
                        '[class*="story-body"]', '[class*="entry-content"]',
                        '[class*="article__content"]', 'main']:
                el = soup.select_one(sel)
                if el:
                    bs_text = el.get_text(separator='\n', strip=True)
                    if len(bs_text) > len(content):
                        content = bs_text
                        break

        if not content or not title:
            return {}

        return {
            'title': title.strip(),
            'url': url,
            'content': content.strip(),
            'published_at': published_at,
            'image_url': image_url,
        }
    except Exception as e:
        print(f"Error in Generic Extractor for {url}: {e}")
    return {}


def extract(url: str) -> List[Dict]:
    try:
        response = httpx.get(
            url, timeout=settings.REQUEST_TIMEOUT,
            headers=HEADERS, follow_redirects=True
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        seen_urls = set()
        articles = []

        for link in soup.find_all('a'):
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # Arabic titles usually >= 20 chars
            if not href or len(text) < 20:
                continue
            if not href.startswith('http'):
                base_url = '/'.join(url.split('/')[:3])
                href = f"{base_url}{href}"
            # Same domain only
            from urllib.parse import urlparse
            if urlparse(href).netloc != urlparse(url).netloc:
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)

            article_data = extract_article_content(href)
            if article_data and len(article_data.get('content', '')) > 200:
                articles.append(article_data)

            if len(articles) >= 8:  # Up from 5
                break

        print(f"Generic extracted {len(articles)} articles from {url}")
        return articles
    except Exception as e:
        print(f"Error scraping links from {url}: {e}")
        return []
