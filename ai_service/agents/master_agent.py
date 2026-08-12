import json
from typing import Dict, Any, List, Optional
from ai_service.agents.writer_agent import WriterAgent

class MasterAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.writer = WriterAgent(api_key=self.api_key)
        
    def process_new_article(self, article_title: str, article_content: str, item_id: int, platforms: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Orchestrates the entire AI content creation process.
        Returns the structural JSON of posts, carousels, and scripts.
        """
        print(f"[Master Agent] Received new article: '{article_title}'. Delegating tasks...")
        
        # 1. Delegate to Writer Agent
        print("[Master Agent] ✍️ Delegating to Writer Agent...")
        content_results = self.writer.write_all(article_title, article_content, platforms=platforms)
        print("[Master Agent] ✅ Writer Agent finished drafting content.")
        
        # Combine results
        return {
            "content": content_results,
            "status": "ready_for_review"
        }

