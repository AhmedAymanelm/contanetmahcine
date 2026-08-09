from typing import List, Dict
import httpx
import json
from bs4 import BeautifulSoup
from app.core.config import settings

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../")))

from app.ai.claude_client import generate_structured_content
from app.ai.schemas import ExtractedArticle
from app.ai.prompts.extraction_prompt import EXTRACTION_SYSTEM_PROMPT, get_extraction_prompt

def extract(url: str) -> List[Dict]:
    """Layer 4: AI Extraction Fallback"""
    try:
        # Fetch the raw HTML
        response = httpx.get(url, timeout=settings.REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Simplify HTML to save Claude tokens
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        prompt = f"""
        Extract the main title, the clean body content (ignoring ads, navigation, footers, etc.), 
        and the publication date if available from the following HTML content.
        
        HTML Content:
        {soup.get_text(separator=' ', strip=True)[:15000]}  # limit text to avoid token limits
        """
        
        schema = ExtractedArticle.model_json_schema()
        result = generate_structured_content(EXTRACTION_SYSTEM_PROMPT, prompt, schema)
        
        if result and len(result.get("content", "")) > 100:
            return [{
                "title": result.get("title", ""),
                "url": url,
                "content": result.get("content", ""),
                "published_at": result.get("published_at", "")
            }]
            
    except Exception as e:
        print(f"Error in AI Extractor for {url}: {e}")
        
    return []
