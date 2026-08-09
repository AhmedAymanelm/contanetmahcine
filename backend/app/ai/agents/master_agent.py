import json
from typing import Dict, Any
from app.ai.agents.writer_agent import WriterAgent
from app.ai.agents.visuals_agent import VisualsAgent

class MasterAgent:
    def __init__(self):
        self.writer = WriterAgent()
        self.visuals = VisualsAgent()
        
    def process_new_article(self, article_title: str, article_content: str, item_id: int) -> Dict[str, Any]:
        """
        Orchestrates the entire content creation process.
        In a fully autonomous system, this agent would use Tool Calling to decide 
        which sub-agent to invoke. For predictability right now, we define the workflow.
        """
        print(f"[Master Agent] Received new article: '{article_title}'. Delegating tasks...")
        
        # 1. Delegate to Writer Agent
        print("[Master Agent] ✍️ Delegating to Writer Agent...")
        content_results = self.writer.write_all(article_title, article_content)
        print("[Master Agent] ✅ Writer Agent finished drafting content.")
        
        # 2. Delegate Carousel generation to Visuals Agent
        print("[Master Agent] 🎨 Delegating carousel rendering to Visuals Agent...")
        carousel_data = content_results.get("carousel", {})
        
        # Only render if we successfully got carousel JSON
        image_paths = []
        if carousel_data and "slides" in carousel_data:
            image_paths = self.visuals.generate_carousel_images(item_id, carousel_data)
            print(f"[Master Agent] ✅ Visuals Agent finished rendering {len(image_paths)} images.")
        else:
            print("[Master Agent] ⚠️ No valid carousel data returned from Writer Agent.")

        # Combine results
        return {
            "content": content_results,
            "generated_images": image_paths,
            "status": "ready_for_review"
        }
