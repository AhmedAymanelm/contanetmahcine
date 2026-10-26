"""
AI Usage Tracker — logs every Claude API call to the DB.
Call log_usage() after any Anthropic response.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Pricing per 1M tokens (Anthropic public pricing, USD) ──────────────────
PRICING = {
    # Sonnet 4.5 / Sonnet 4
    "claude-sonnet-4-5":            {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-0":            {"input": 3.00, "output": 15.00},
    "claude-sonnet-4":              {"input": 3.00, "output": 15.00},
    # Haiku 3.5
    "claude-3-5-haiku-20241022":    {"input": 0.80, "output": 4.00},
    "claude-3-5-haiku":             {"input": 0.80, "output": 4.00},
    # Sonnet 3.5
    "claude-3-5-sonnet-20241022":   {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20240620":   {"input": 3.00, "output": 15.00},
    # Opus 3
    "claude-3-opus-20240229":       {"input": 15.00, "output": 75.00},
}

def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return estimated cost in USD."""
    key = next((k for k in PRICING if model.startswith(k)), None)
    if not key:
        # Default fallback — Sonnet pricing
        rate_in, rate_out = 3.00, 15.00
    else:
        rate_in  = PRICING[key]["input"]
        rate_out = PRICING[key]["output"]
    return round((input_tokens * rate_in + output_tokens * rate_out) / 1_000_000, 8)


def log_usage(
    operation: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    raw_article_id: Optional[int] = None,
):
    """
    Persist a single AI usage record.
    Safe to call from anywhere — silently ignores DB errors to avoid
    breaking the main generation flow.
    """
    try:
        from app.db.session import SessionLocal
        from app.models.ai_usage_log import AiUsageLog

        cost = _estimate_cost(model, input_tokens, output_tokens)
        db = SessionLocal()
        try:
            record = AiUsageLog(
                operation=operation,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                estimated_cost_usd=cost,
                raw_article_id=raw_article_id,
            )
            db.add(record)
            db.commit()
            logger.debug(
                f"[AI Usage] {operation} | {model} | "
                f"in={input_tokens} out={output_tokens} cost=${cost:.6f}"
            )
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[AI Usage] Failed to log usage: {e}")
