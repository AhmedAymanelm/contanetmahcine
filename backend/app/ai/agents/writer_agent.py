from app.ai.agents.base_agent import AgentClient, AgentConfig
from app.ai.schemas import PostContent, CarouselContent, VideoScript
from app.ai.prompts.post_prompt import get_post_prompt
from app.ai.prompts.carousel_prompt import get_carousel_prompt
from app.ai.prompts.video_script_prompt import get_video_script_prompt
from typing import Dict, Any

class WriterAgent:
    def __init__(self):
        self.client = AgentClient()
        self.config = AgentConfig(
            name="The Viral Content Writer",
            role="Expert Social Media Copywriter and Strategist",
            goal="Transform raw news and articles into engaging, viral content tailored for specific platforms.",
            backstory="You are a top-tier digital marketer who studied the best content creators (like @ak4app). You know how to hook an audience in 8 words, how to write conversational and highly engaging carousels, and how to craft calls-to-action that drive massive comments. You strictly follow viral copywriting rules."
        )

    def write_posts(self, title: str, content: str) -> dict:
        prompt = get_post_prompt(title, content)
        return self.client.execute_structured_task(self.config, prompt, PostContent)

    def write_carousel(self, title: str, content: str) -> dict:
        prompt = get_carousel_prompt(title, content)
        return self.client.execute_structured_task(self.config, prompt, CarouselContent)

    def write_video_script(self, title: str, content: str) -> dict:
        prompt = get_video_script_prompt(title, content)
        return self.client.execute_structured_task(self.config, prompt, VideoScript)

    def write_all(self, title: str, content: str) -> Dict[str, Any]:
        """Generates all content sequentially"""
        return {
            "posts": self.write_posts(title, content),
            "carousel": self.write_carousel(title, content),
            "video_script": self.write_video_script(title, content)
        }
