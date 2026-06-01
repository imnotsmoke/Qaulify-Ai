"""
Agent handover endpoints.

Provides endpoints for real estate agents to:
- View their assigned leads
- Take over a conversation manually
- Mark follow-ups as complete
"""
import logging

from flask import Blueprint, request, jsonify
from app.models import db, Lead, Conversation

logger = logging.getLogger(__name__)

agent_bp = Blueprint("agent", __name__, url_prefix="/api/agent")


@agent_bp.route("/leads", methods=["GET"])
def list_leads():
    """
    List all leads, optionally filtered by qualification_status.

    Query parameters:
        status (str, optional): filter by qualification_status
        limit (int, optional): max results (default 50, max 200)
    """
    status_filter = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 200)

    query = Lead.query.order_by(Lead.updated_at.desc())
    if status_filter:
        query = query.filter(Lead.qualification_status == status_filter)

    leads = query.limit(limit).all()
    return jsonify({"leads": [l.to_dict() for l in leads]}), 200


@agent_bp.route("/leads/<lead_id>", methods=["GET"])
def get_lead(lead_id: str):
    """Get a single lead by ID with full conversation history."""
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    conversations = Conversation.query.filter_by(lead_id=lead_id)\
        .order_by(Conversation.updated_at.desc()).all()

    return jsonify({
        "lead": lead.to_dict(),
        "conversations": [
            {
                "id": c.id,
                "session_state": c.session_state,
                "messages": c.messages,
                "context": c.context,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in conversations
        ],
    }), 200


@agent_bp.route("/conversations/<conversation_id>/takeover", methods=["POST"])
def takeover_conversation(conversation_id: str):
    """
    Allow an agent to take over a conversation manually.
    Sets the conversation state to 'agent_handover'.
    """
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404

    conversation.session_state = "agent_handover"
    db.session.commit()

    logger.info("Conversation %s taken over by agent", conversation_id)
    return jsonify({
        "status": "ok",
        "conversation_id": conversation_id,
        "session_state": conversation.session_state,
    }), 200


@agent_bp.route("/leads/<lead_id>/follow-up", methods=["POST"])
def mark_follow_up(lead_id: str):
    """Mark a lead's follow-up as sent."""
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    lead.follow_up_sent = True
    db.session.commit()

    logger.info("Follow-up marked as sent for lead %s", lead_id)
    return jsonify({"status": "ok", "follow_up_sent": True}), 200