from pydantic import BaseModel, Field
from typing import List

class PostContent(BaseModel):
    unified_post: str = Field(..., description="One unified Arabic post used for all platforms (Facebook, Instagram, X, Threads, Snapchat, TikTok). Same text everywhere.")
    linkedin_post: str = Field(..., description="Professional post in ENGLISH ONLY for LinkedIn. Adapts the same news for a professional English-speaking audience.")

from typing import List, Optional

class CarouselSlide(BaseModel):
    heading: str = Field(..., description="Short catchy heading for the slide (max 6 words)")
    body: str = Field(..., description="Main content or insight for the slide (1-2 sentences max)")
    tips_list: Optional[List[str]] = Field(None, description="Optional list of 3-5 bullet points (tips, facts, or steps)")
    left_column_title: Optional[str] = Field(None, description="Title for left column if using two-column layout")
    left_column_items: Optional[List[str]] = Field(None, description="Items for left column")
    right_column_title: Optional[str] = Field(None, description="Title for right column if using two-column layout")
    right_column_items: Optional[List[str]] = Field(None, description="Items for right column")

class CarouselContent(BaseModel):
    title: str = Field(..., description="Overall title of the carousel")
    slides: List[CarouselSlide] = Field(..., min_length=5, max_length=7, description="List of EXACTLY 5 to 7 slides. You MUST generate at least 5 slides.")

class VideoScript(BaseModel):
    hook: str = Field(..., description="Catchy opening hook (first 3 seconds)")
    body: str = Field(..., description="Main talking points and value delivery")
    call_to_action: str = Field(..., description="Closing CTA (e.g., follow, comment)")
    visual_cues: str = Field(..., description="Suggestions for text on screen or b-roll")

# ── REEL: Video-ready slides — each slide = one screen in the final video ────
class ReelSlide(BaseModel):
    text: str = Field(..., description="The MAIN text displayed on screen. Bold, punchy, 2-15 words max. This is the ONLY thing the viewer reads.")
    note: Optional[str] = Field(None, description="Optional small subtitle or stat shown below the main text (max 10 words). Use for numbers, percentages, or a single supporting fact.")

class ReelContent(BaseModel):
    slides: List[ReelSlide] = Field(..., min_length=5, max_length=9, description="5 to 9 slides. Each slide is ONE screen. First slide = hook. Last slide = CTA.")

class ExtractedArticle(BaseModel):
    title: str = Field(..., description="The main headline of the article")
    content: str = Field(..., description="The clean main body text of the article")
    published_at: str = Field(default="", description="The publication date if found")
