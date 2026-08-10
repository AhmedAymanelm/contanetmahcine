from typing import Dict, Any, List, Optional
from app.ai.agents.master_agent import MasterAgent

# Keep these wrapper functions for backwards compatibility with the API router
def generate_posts(article_title: str, article_content: str) -> dict:
    agent = MasterAgent()
    return agent.writer.write_posts(article_title, article_content)

def generate_carousel(article_title: str, article_content: str,
                      platforms: Optional[List[str]] = None) -> dict:
    agent = MasterAgent()
    return agent.writer.write_carousel(article_title, article_content, platforms=platforms)

def generate_video_script(article_title: str, article_content: str) -> dict:
    agent = MasterAgent()
    return agent.writer.write_video_script(article_title, article_content)

def generate_all_content(title: str, content: str,
                         platforms: Optional[List[str]] = None) -> Dict[str, Any]:
    """Generates all 3 types of content via the Writer Agent"""
    agent = MasterAgent()
    return agent.writer.write_all(title, content, platforms=platforms)

def generate_selected_content(title: str, content: str, formats: list,
                              platforms: Optional[List[str]] = None) -> Dict[str, Any]:
    """Generates only the selected types of content via the Writer Agent"""
    agent = MasterAgent()
    results = {}
    if "POST" in formats:
        results["posts"]        = agent.writer.write_posts(title, content)
    if "CAROUSEL" in formats:
        results["carousel"]     = agent.writer.write_carousel(title, content, platforms=platforms)
    if "VIDEO_SCRIPT" in formats:
        results["video_script"] = agent.writer.write_video_script(title, content)
    return results
