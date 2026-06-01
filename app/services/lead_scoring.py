"""
Lead scoring service.

Calculates a lead score (0.0 – 1.0) based on:
- Budget alignment with portfolio
- Urgency level
- Engagement depth (messages exchanged)
- Qualification status progression
"""
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Scoring weights
WEIGHT_BUDGET = 0.35
WEIGHT_URGENCY = 0.25
WEIGHT_ENGAGEMENT = 0.20
WEIGHT_QUALIFICATION = 0.20


def score_lead(
    budget: Optional[float],
    urgency: Optional[str],
    message_count: int,
    qualification_status: str,
) -> float:
    """
    Compute a lead score from 0.0 (cold) to 1.0 (hot).

    Args:
        budget: Lead's stated budget (or None if unknown).
        urgency: 'immediate', 'this_month', 'flexible', or None.
        message_count: Number of messages exchanged.
        qualification_status: Current status in the pipeline.

    Returns:
        Score between 0.0 and 1.0.
    """
    score = 0.0

    # --- Budget score ---
    # If budget is provided and reasonable (> 0), high confidence
    budget_score = 0.5 if budget is not None and budget > 0 else 0.0
    score += WEIGHT_BUDGET * budget_score

    # --- Urgency score ---
    urgency_map = {
        "immediate": 1.0,
        "this_month": 0.7,
        "flexible": 0.3,
    }
    urgency_score = urgency_map.get(urgency, 0.1) if urgency else 0.0
    score += WEIGHT_URGENCY * urgency_score

    # --- Engagement score ---
    # More messages = higher engagement (capped at 20 messages)
    engagement_score = min(message_count / 20.0, 1.0)
    score += WEIGHT_ENGAGEMENT * engagement_score

    # --- Qualification status score ---
    status_map = {
        "new": 0.0,
        "qualifying": 0.3,
        "qualified": 0.8,
        "disqualified": 0.0,
        "follow_up": 0.5,
    }
    status_score = status_map.get(qualification_status, 0.0)
    score += WEIGHT_QUALIFICATION * status_score

    # Clamp to [0.0, 1.0]
    final_score = max(0.0, min(1.0, score))
    logger.debug("Lead score computed: %.2f (budget=%.2f, urgency=%.2f, engage=%.2f, status=%.2f)",
                 final_score, budget_score, urgency_score, engagement_score, status_score)
    return round(final_score, 2)