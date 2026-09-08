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
    """Extract best image: JSON-LD > og:image > twitter:image > article img."""
    from urllib.parse import urlparse

    def make_absolute(src: str) -> str:
        if not src:
            return ''
        src = src.strip()
        if src.startswith('//'):
            return 'https:' + src
        if src.startswith('/'):
            p = urlparse(base_url)
            return f"{p.scheme}://{p.netloc}{src}"
        return src

    def is_meta_img(src: str) -> bool:
        """Minimal filter for og:image / JSON-LD — just needs to be a real http URL."""
        if not src:
            return False
        return src.startswith('http') and not src.lower().endswith('.svg')

    def is_body_img(src: str) -> bool:
        """Stricter filter for images scanned from body HTML — skip nav/icon images."""
        if not src or not src.startswith('http'):
            return False
        low = src.lower()
        # Skip only very clearly bad patterns (not 'logo' — article covers often have brand logos)
        bad = ['.gif', 'pixel', 'tracker', 'blank', 'spacer', '1x1', 'ad_', '_ad',
               'doubleclick', 'googletagmanager', 'analytics']
        return not any(b in low for b in bad)

    # 1. JSON-LD structured data (most reliable — trust fully)
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            import json as _json
            data = _json.loads(script.string or '{}')
            items = data if isinstance(data, list) else [data]
            for item in items:
                img = item.get('image')
                if isinstance(img, str):
                    src = make_absolute(img)
                    if is_meta_img(src):
                        return src
                if isinstance(img, dict):
                    url_ = img.get('url', img.get('contentUrl', ''))
                    src = make_absolute(url_)
                    if is_meta_img(src):
                        return src
                if isinstance(img, list) and img:
                    first = img[0]
                    url_ = first if isinstance(first, str) else first.get('url', '')
                    src = make_absolute(url_)
                    if is_meta_img(src):
                        return src
        except Exception:
            pass

    # 2. og:image / twitter:image — trust fully
    for prop in ['og:image', 'twitter:image', 'article:image']:
        tag = (soup.find('meta', property=prop) or
               soup.find('meta', attrs={'name': prop}))
        if tag and tag.get('content'):
            src = make_absolute(tag['content'].strip())
            if is_meta_img(src):
                return src


    # 3. First large image inside article/main content area
    for container_sel in ['article', 'main', '[class*="article"]',
                           '[class*="post-content"]', '[class*="entry-content"]',
                           '[class*="story-body"]', 'body']:
        container = soup.select_one(container_sel)
        if not container:
            continue
        for img in container.find_all('img'):
            # Collect all possible src attributes
            for attr in ['src', 'data-src', 'data-lazy-src', 'data-original',
                         'data-lazy', 'data-full-src', 'data-image']:
                raw = img.get(attr, '')
                if raw:
                    src = make_absolute(raw)
                    if not is_body_img(src):
                        continue
                    # Skip tiny images
                    w = img.get('width', '') or img.get('data-width', '')
                    h = img.get('height', '') or img.get('data-height', '')
                    if w and str(w).isdigit() and int(w) < 200:
                        continue
                    if h and str(h).isdigit() and int(h) < 150:
                        continue
                    return src
            # Try srcset
            srcset = img.get('srcset', '')
            if srcset:
                # Pick the largest from srcset
                parts = [p.strip() for p in srcset.split(',') if p.strip()]
                if parts:
                    src = make_absolute(parts[-1].split()[0])
                    if is_body_img(src):
                        return src
        if container_sel == 'body':
            break  # don't repeat

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
