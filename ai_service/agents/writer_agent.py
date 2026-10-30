from ai_service.agents.base_agent import AgentClient, AgentConfig
from ai_service.schemas import PostContent, CarouselContent, VideoScript, ReelContent
from ai_service.prompts.post_prompt import get_post_prompt
from ai_service.prompts.carousel_prompt import get_carousel_prompt, CAROUSEL_SYSTEM_PROMPT
from ai_service.prompts.video_script_prompt import get_video_script_prompt
from ai_service.prompts.reel_prompt import get_reel_prompt, REEL_SYSTEM_PROMPT
from typing import Dict, Any, List, Optional

class WriterAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = AgentClient(api_key=self.api_key)
        self.config = AgentConfig(
            name="The Viral Content Writer",
            role="Expert Social Media Copywriter and Strategist",
            goal="Transform raw news and articles into engaging, viral content tailored for specific platforms.",
            backstory="You are a top-tier digital marketer who studied the best content creators (like @ak4app). You know how to hook an audience in 8 words, how to write conversational and highly engaging carousels, and how to craft calls-to-action that drive massive comments. You strictly follow viral copywriting rules."
        )


    def write_posts(self, title: str, content: str) -> dict:
        prompt = get_post_prompt(title, content)
        return self.client.execute_structured_task(self.config, prompt, PostContent)

    def write_carousel(self, title: str, content: str, platforms: Optional[List[str]] = None) -> dict:
        """
        Generate carousel content.
        Language logic:
        - Default: Arabic (for Instagram, Facebook, all Arabic platforms)
        - English ONLY when LinkedIn is the sole platform selected
        - If LinkedIn is selected WITH other platforms: generate Arabic (linkedin_slides
          will be auto-translated by _ensure_english_linkedin in the publish flow)
        """
        platforms = platforms or []
        plats_upper = [p.upper() for p in platforms]

        is_li_only = (
            bool(platforms) and
            all(("LI" in p or "LINKEDIN" in p) for p in plats_upper)
        )

        language = "english" if is_li_only else "arabic"
        prompt = get_carousel_prompt(title, content, language=language)
        return self.client.execute_structured_task(self.config, prompt, CarouselContent)

    def write_video_script(self, title: str, content: str) -> dict:
        prompt = get_video_script_prompt(title, content)
        return self.client.execute_structured_task(self.config, prompt, VideoScript)

    def write_reel(self, title: str, content: str) -> dict:
        prompt = get_reel_prompt(title, content)
        reel_config = AgentConfig(
            name="Reel Slide Writer",
            role="Visual Headline Writer for Short-Form Video",
            goal="Write ultra-short punchy slide text (3-8 words max per slide) for Reels/TikTok videos.",
            backstory=REEL_SYSTEM_PROMPT,
        )
        return self.client.execute_structured_task(reel_config, prompt, ReelContent)

    def write_all(self, title: str, content: str, platforms: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generates all content sequentially"""
        return {
            "posts":        self.write_posts(title, content),
            "carousel":     self.write_carousel(title, content, platforms=platforms),
            "video_script": self.write_video_script(title, content),
            "reel":         self.write_reel(title, content),
        }
