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
    """Check if a URL returns a valid RSS/Atom feed."""
    try:
        response = httpx.get(url, timeout=settings.REQUEST_TIMEOUT, headers=HEADERS, follow_redirects=True)
        ct = response.headers.get("Content-Type", "")
        body = response.text.lower()[:500]
        return ("xml" in ct or "rss" in ct or "atom" in ct or
                "rss" in body or "<feed" in body or "<channel" in body)
    except Exception:
        return False

def discover_rss(url: str) -> Optional[str]:
    from urllib.parse import urlparse

    # 1. Direct URL is already RSS?
    if _is_valid_rss(url):
        return url

    parsed = urlparse(url)
    # Extract meaningful path segments to prefer section-specific RSS
    path_segments = [p for p in parsed.path.split('/') if p and len(p) > 2]

    # 2. Auto-discover from page HTML - collect ALL RSS links first
    candidates = []
    try:
        response = httpx.get(url, timeout=settings.REQUEST_TIMEOUT, headers=HEADERS, follow_redirects=True)
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all('link', type=lambda t: t and ('rss' in t or 'atom' in t)):
            href = link.get('href', '')
            if not href:
                continue
            if not href.startswith('http'):
                base = f"{parsed.scheme}://{parsed.netloc}"
                href = f"{base}{href}"
            candidates.append(href)

    except Exception as e:
        print(f"Error in RSS auto-discovery for {url}: {e}")

    # 3. Try suffix-based discovery on the full path URL first (section-specific)
    base_url = url.rstrip("/")
    for suffix in ["/feed", "/rss", "/rss.xml", "/atom.xml", "/?feed=rss2"]:
        candidates.append(f"{base_url}{suffix}")

    # 4. Also try domain-root suffixes as a fallback
    domain_root = f"{parsed.scheme}://{parsed.netloc}"
    for suffix in ["/feed", "/rss", "/rss.xml", "/atom.xml"]:
        candidates.append(f"{domain_root}{suffix}")

    # 5. Score candidates: prefer those whose URL contains the source path segments
    def path_score(rss_url: str) -> int:
        rss_lower = rss_url.lower()
        return sum(1 for seg in path_segments if seg.lower() in rss_lower)

    # Sort by path relevance (highest score = most specific match)
    candidates.sort(key=path_score, reverse=True)

    for candidate in candidates:
        if _is_valid_rss(candidate):
            print(f"RSS discovered for {url}: {candidate} (path_score={path_score(candidate)})")
            return candidate

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

def _rss_matches_source(rss_url: str, source_url: str, feed_titles: list) -> bool:
    """
    Verify the discovered RSS is relevant to the source URL.
    If source has a specific path (e.g. /tag/ai/) but RSS is from root,
    sample titles to check if they seem related.
    """
    from urllib.parse import urlparse
    from app.services.ingestion.relevance_filter import is_tech_relevant

    parsed_source = urlparse(source_url)
    parsed_rss    = urlparse(rss_url)

    # If RSS is on a different domain, reject
    if parsed_rss.netloc and parsed_source.netloc:
        source_domain = parsed_source.netloc.replace('www.', '')
        rss_domain    = parsed_rss.netloc.replace('www.', '')
        # Allow different subdomains (e.g. feeds.bbci.co.uk for bbc.com)
        if not (rss_domain.endswith(source_domain.split('.')[-2] + '.' + source_domain.split('.')[-1]) or
                source_domain.endswith(rss_domain.split('.')[-2] + '.' + rss_domain.split('.')[-1])):
            print(f"RSS domain mismatch: {rss_domain} vs {source_domain}")
            return False

    # If source has a meaningful specific path, verify RSS articles are tech-relevant
    path_segs = [p for p in parsed_source.path.split('/') if p and len(p) > 2]
    if path_segs and feed_titles:
        relevant = sum(1 for t in feed_titles[:5] if is_tech_relevant(t))
        total = min(5, len(feed_titles))
        if total > 0 and relevant == 0:
            print(f"RSS sanity check failed: 0/{total} titles are tech-relevant for {source_url}")
            return False

    return True


def extract(url: str) -> List[Dict]:
    rss_url = discover_rss(url)
    if not rss_url:
        return []
    try:
        parsed_feed = feedparser.parse(rss_url)
        if not parsed_feed.entries:
            return []

        # Sanity check: is this RSS actually relevant to our source URL?
        sample_titles = [e.get('title', '') for e in parsed_feed.entries[:5]]
        if not _rss_matches_source(rss_url, url, sample_titles):
            print(f"Skipping RSS {rss_url} — not relevant to source {url}")
            return []

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
