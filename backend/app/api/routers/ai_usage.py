"""
AI Usage API — token consumption and cost tracking for Claude API calls.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional

from app.api.deps import get_db
from app.models.ai_usage_log import AiUsageLog

router = APIRouter()


def _get_window(days: int, now: datetime):
    if days <= 0:
        return datetime(2000, 1, 1, tzinfo=timezone.utc), None
    return now - timedelta(days=days), now - timedelta(days=days*2)


@router.get("/overview")
def get_usage_overview(
    db: Session = Depends(get_db),
    days: int = Query(30, description="0=all time, else last N days"),
):
    now = datetime.now(timezone.utc)
    start, prev_start = _get_window(days, now)

    # ── Current period ─────────────────────────────────────────────────────
    logs = db.query(AiUsageLog).filter(AiUsageLog.created_at >= start).all()

    total_calls   = len(logs)
    total_input   = sum(r.input_tokens  for r in logs)
    total_output  = sum(r.output_tokens for r in logs)
    total_tokens  = sum(r.total_tokens  for r in logs)
    total_cost    = round(sum(r.estimated_cost_usd for r in logs), 6)

    # ── Previous period (for delta) ────────────────────────────────────────
    if prev_start and days > 0:
        prev_logs = db.query(AiUsageLog).filter(
            AiUsageLog.created_at >= prev_start,
            AiUsageLog.created_at < start,
        ).all()
        prev_cost   = round(sum(r.estimated_cost_usd for r in prev_logs), 6)
        prev_calls  = len(prev_logs)
        prev_tokens = sum(r.total_tokens for r in prev_logs)
    else:
        prev_cost = prev_calls = prev_tokens = 0

    # ── Breakdown by operation ─────────────────────────────────────────────
    op_stats: dict = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
    for r in logs:
        op_stats[r.operation]["calls"]         += 1
        op_stats[r.operation]["input_tokens"]  += r.input_tokens
        op_stats[r.operation]["output_tokens"] += r.output_tokens
        op_stats[r.operation]["cost_usd"]      = round(op_stats[r.operation]["cost_usd"] + r.estimated_cost_usd, 8)

    by_operation = [
        {
            "operation": op,
            **stats,
            "cost_usd": round(stats["cost_usd"], 6),
        }
        for op, stats in sorted(op_stats.items(), key=lambda x: -x[1]["cost_usd"])
    ]

    # ── Breakdown by model ─────────────────────────────────────────────────
    model_stats: dict = defaultdict(lambda: {"calls": 0, "total_tokens": 0, "cost_usd": 0.0})
    for r in logs:
        model_stats[r.model]["calls"]        += 1
        model_stats[r.model]["total_tokens"] += r.total_tokens
        model_stats[r.model]["cost_usd"]     = round(model_stats[r.model]["cost_usd"] + r.estimated_cost_usd, 8)

    by_model = [
        {"model": m, **s, "cost_usd": round(s["cost_usd"], 6)}
        for m, s in sorted(model_stats.items(), key=lambda x: -x[1]["cost_usd"])
    ]

    # ── Daily cost trend (last 14 days) ───────────────────────────────────
    trend_start = now - timedelta(days=14)
    trend_logs  = db.query(AiUsageLog).filter(AiUsageLog.created_at >= trend_start).all()
    daily: dict = defaultdict(float)
    for r in trend_logs:
        day = r.created_at.strftime("%Y-%m-%d")
        daily[day] = round(daily[day] + r.estimated_cost_usd, 8)

    daily_trend = [
        {"date": d, "cost_usd": round(c, 6)}
        for d, c in sorted(daily.items())
    ]

    # ── Recent log entries ─────────────────────────────────────────────────
    recent = db.query(AiUsageLog).order_by(AiUsageLog.created_at.desc()).limit(50).all()
    recent_entries = [
        {
            "id":           r.id,
            "operation":    r.operation,
            "model":        r.model,
            "input_tokens": r.input_tokens,
            "output_tokens":r.output_tokens,
            "total_tokens": r.total_tokens,
            "cost_usd":     r.estimated_cost_usd,
            "created_at":   r.created_at.isoformat(),
        }
        for r in recent
    ]

    return {
        "period_days": days,
        "summary": {
            "total_calls":   total_calls,
            "total_tokens":  total_tokens,
            "input_tokens":  total_input,
            "output_tokens": total_output,
            "cost_usd":      total_cost,
            "prev_cost_usd": prev_cost,
            "prev_calls":    prev_calls,
            "prev_tokens":   prev_tokens,
        },
        "by_operation": by_operation,
        "by_model":     by_model,
        "daily_trend":  daily_trend,
        "recent_logs":  recent_entries,
        "generated_at": now.isoformat(),
    }
