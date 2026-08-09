from app.ai.agents.base_agent import AgentClient, AgentConfig
from app.services.carousel_renderer import render_carousel_sync
from typing import Dict, Any, List

class VisualsAgent:
    def __init__(self):
        self.client = AgentClient()
        self.config = AgentConfig(
            name="The Creative Director",
            role="Expert Graphic Designer and Art Director",
            goal="Take the structural content provided by the Writer Agent and visually render it into high-quality, professional carousel images using the Playwright rendering engine.",
            backstory="You have an eye for design, typography, and visual hierarchy. You ensure every slide looks premium and adheres to the @ak4app aesthetic. You don't write the content, you just bring it to life visually."
        )

    def generate_carousel_images(self, content_id: int, carousel_data: Dict[str, Any]) -> List[str]:
        """
        Acts as a 'Tool' for the Master Agent. 
        Takes the JSON from the Writer and triggers the Playwright renderer.
        """
        # We can add intelligence here later (e.g., AI choosing the specific theme based on emotion of the text)
        print(f"[{self.config.name}] Rendering carousel for item {content_id}...")
        
        try:
            # Generate the images using our playwright engine
            image_paths = render_carousel_sync(content_id, carousel_data)
            print(f"[{self.config.name}] Successfully generated {len(image_paths)} slides.")
            return image_paths
        except Exception as e:
            print(f"[{self.config.name}] Error rendering carousel: {e}")
            return []
