"""
WhatsApp message handler — coordinates the AI conversation flow.

Thin entry point that delegates heavy lifting to ConversationFlow
and services.  Keeps route handlers clean.
"""
import logging
from typing import Optional

from flask import current_app

from app.models import db, Lead, Conversation
from app.conversation.flow import ConversationFlow, EXTRACTION_FUNCTIONS
from app.services.ai_service import AIService
from app.services.whatsapp_service import WhatsAppService
from app.utils.delays import human_delay

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_lead(phone: str) -> Lead:
    """Look up a lead by phone number or create a new one."""
    lead = Lead.query.filter_by(phone=phone).first()
    if not lead:
        lead = Lead(phone=phone, qualification_status="new")
        db.session.add(lead)
        db.session.commit()
        logger.info("Created new lead: %s", phone)
    else:
        logger.info("Found existing lead: %s (status=%s)", phone, lead.qualification_status)
    return lead


def _get_or_create_conversation(lead: Lead) -> Conversation:
    """Get the most recent active conversation for a lead, or create one."""
    conv = Conversation.query.filter_by(lead_id=lead.id)\
        .order_by(Conversation.updated_at.desc()).first()
    if not conv:
        conv = Conversation(
            lead_id=lead.id,
            session_state="greeting",
            messages=[],
            context={},
        )
        db.session.add(conv)
        db.session.commit()
        logger.info("Created new conversation for lead %s", lead.id)
    return conv


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def process_incoming_message(
    from_number: str,
    text_body: str,
) -> bool:
    """
    Process a single WhatsApp text message through the AI conversation engine.

    Delegates message storage, AI prompting, data extraction, and state
    transitions to ``ConversationFlow``, then sends the reply.
    """
    # 1. Load / create lead and conversation
    lead = _get_or_create_lead(from_number)
    conversation = _get_or_create_conversation(lead)

    # Reset completed conversations
    if conversation.session_state == "done":
        conversation.session_state = "greeting"
        conversation.messages = []
        conversation.context = {}
        db.session.commit()

    flow = ConversationFlow(lead, conversation)

    # 2. Save incoming user message
    flow.add_message("user", text_body)

    # 3. Call OpenAI
    api_key = current_app.config.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.error("OPENAI_API_KEY not configured")
        return False

    ai_service = AIService(api_key=api_key)
    ai_messages = flow.build_ai_messages()
    ai_response = ai_service.chat_with_functions(
        messages=ai_messages,
        functions=EXTRACTION_FUNCTIONS,
        function_call="auto",
    )

    if ai_response is None:
        logger.error("AI service returned None — check API key and quota")
        return False

    reply_text, function_data = ai_response

    # 4. Apply extracted data and handle transitions
    if function_data:
        flow.handle_extracted_data(function_data)

    # 5. Save AI response
    flow.add_message("assistant", reply_text)

    # 6. Human-like delay
    human_delay(message_length=len(reply_text), complexity="medium")

    # 7. Send reply via WhatsApp
    wa_token = current_app.config.get("WHATSAPP_TOKEN", "")
    wa_phone_id = current_app.config.get("WHATSAPP_PHONE_NUMBER_ID", "")

    if not wa_token or not wa_phone_id:
        logger.warning("WhatsApp credentials not configured — reply logged but not sent")
        logger.info("AI reply to %s: %s", from_number, reply_text[:200])
        return True

    wa_service = WhatsAppService(token=wa_token, phone_number_id=wa_phone_id)
    success = wa_service.send_text(to=from_number, body=reply_text)

    if success:
        logger.info("Replied to %s: %.100s", from_number, reply_text)
    else:
        logger.warning("Failed to send reply to %s", from_number)

    return success