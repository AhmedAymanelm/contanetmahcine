from sqlalchemy import Column, Integer, String, DateTime, Float
from datetime import datetime, timezone
from app.models.base import Base


class AiUsageLog(Base):
    """
    Tracks every Claude API call: tokens in/out, model, operation, estimated cost.
    """
    __tablename__ = "ai_usage_logs"

    id              = Column(Integer, primary_key=True, index=True)

    # What generated this call
    operation       = Column(String, nullable=False)   # e.g. "generate_post", "generate_carousel", "ai_extractor", "content_ideas"
    model           = Column(String, nullable=False)   # e.g. "claude-sonnet-4-5"

    # Token counts (from Anthropic response.usage)
    input_tokens    = Column(Integer, default=0)
    output_tokens   = Column(Integer, default=0)
    total_tokens    = Column(Integer, default=0)

    # Estimated cost in USD  (based on public Anthropic pricing)
    estimated_cost_usd = Column(Float, default=0.0)

    # Optional reference to the article that triggered this
    raw_article_id  = Column(Integer, nullable=True)

    created_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
