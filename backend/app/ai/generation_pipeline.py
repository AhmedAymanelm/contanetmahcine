from typing import Dict, Any
from app.ai.agents.master_agent import MasterAgent

# Keep these wrapper functions for backwards compatibility with the API router for now
def generate_posts(article_title: str, article_content: str) -> dict:
    agent = MasterAgent()
    return agent.writer.write_posts(article_title, article_content)

def generate_carousel(article_title: str, article_content: str) -> dict:
    agent = MasterAgent()
    return agent.writer.write_carousel(article_title, article_content)

def generate_video_script(article_title: str, article_content: str) -> dict:
    agent = MasterAgent()
    return agent.writer.write_video_script(article_title, article_content)

def generate_all_content(title: str, content: str) -> Dict[str, Any]:
    """Generates all 3 types of content via the Writer Agent"""
    agent = MasterAgent()
    return agent.writer.write_all(title, content)
