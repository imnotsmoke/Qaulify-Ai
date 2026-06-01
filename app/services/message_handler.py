"""
WhatsApp message handler — orchestrates the AI conversation flow.

Takes an incoming WhatsApp message, looks up/creates the lead,
runs it through the AI conversation engine, updates state,
and sends a reply.
"""
import logging
import json
from typing import Optional

from flask import current_app

from app.models import db, Lead, Conversation
from app.conversation.flow import ConversationFlow, ConversationState
from app.conversation.prompts import SYSTEM_PROMPT
from app.services.ai_service import AIService
from app.services.whatsapp_service import WhatsAppService
from app.services.affordability import calculate_affordability
from app.services.lead_scoring import score_lead
from app.utils.delays import human_delay
from app.utils.templates import greeting_new, greeting_returning

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAI function definitions for structured data extraction
# ---------------------------------------------------------------------------

EXTRACTION_FUNCTIONS = [
    {
        "name": "extract_lead_data",
        "description": "Extract structured lead qualification data from the conversation.",
        "parameters": {
            "type": "object",
            "properties": {
                "buy_or_rent": {
                    "type": "string",
                    "enum": ["buy", "rent", None],
                    "description": "Whether the lead wants to buy or rent.",
                },
                "property_type": {
                    "type": "string",
                    "description": "Type of property (apartment, house, townhouse, studio, etc.)",
                },
                "budget": {
                    "type": "number",
                    "description": "Lead's stated budget in dollars.",
                },
                "income": {
                    "type": "number",
                    "description": "Lead's stated annual household income in dollars.",
                },
                "urgency": {
                    "type": "string",
                    "enum": ["immediate", "this_month", "flexible", None],
                    "description": "How soon the lead wants to move.",
                },
                "name": {
                    "type": "string",
                    "description": "Lead's name if provided.",
                },
                "email": {
                    "type": "string",
                    "description": "Lead's email address if provided.",
                },
                "requested_handover": {
                    "type": "boolean",
                    "description": "Whether the lead asked to speak to a human agent.",
                },
                "requested_viewing": {
                    "type": "boolean",
                    "description": "Whether the lead wants to book a viewing.",
                },
            },
            "required": [],
        },
    }
]


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


def _apply_extracted_data(lead: Lead, flow: ConversationFlow, data: dict) -> None:
    """
    Update the lead model and conversation context with data extracted
    from the AI response via function calling.
    """
    changed = False

    if data.get("buy_or_rent") and not lead.buy_or_rent:
        lead.buy_or_rent = data["buy_or_rent"]
        flow.update_context("buy_or_rent", data["buy_or_rent"])
        changed = True
        logger.info("Lead %s: buy_or_rent -> %s", lead.id, data["buy_or_rent"])

    if data.get("property_type") and not lead.property_type:
        lead.property_type = data["property_type"]
        flow.update_context("property_type", data["property_type"])
        changed = True
        logger.info("Lead %s: property_type -> %s", lead.id, data["property_type"])

    if data.get("budget") is not None and lead.budget is None:
        lead.budget = data["budget"]
        flow.update_context("budget", data["budget"])
        changed = True
        logger.info("Lead %s: budget -> %s", lead.id, data["budget"])

    if data.get("income") is not None and lead.income is None:
        lead.income = data["income"]
        flow.update_context("income", data["income"])
        changed = True
        logger.info("Lead %s: income -> %s", lead.id, data["income"])

    if data.get("urgency") and not lead.urgency:
        lead.urgency = data["urgency"]
        flow.update_context("urgency", data["urgency"])
        changed = True
        logger.info("Lead %s: urgency -> %s", lead.id, data["urgency"])

    if data.get("name") and not lead.name:
        lead.name = data["name"]
        flow.update_context("name", data["name"])
        changed = True
        logger.info("Lead %s: name -> %s", lead.id, data["name"])

    if data.get("email") and not lead.email:
        lead.email = data["email"]
        flow.update_context("email", data["email"])
        changed = True
        logger.info("Lead %s: email -> %s", lead.id, data["email"])

    if data.get("requested_handover"):
        flow.update_context("requested_handover", True)
        logger.info("Lead %s: requested handover", lead.id)

    if data.get("requested_viewing"):
        lead.viewing_requested = True
        flow.update_context("requested_viewing", True)
        changed = True
        logger.info("Lead %s: requested viewing", lead.id)

    if changed:
        db.session.commit()


def _compute_qualification_status(lead: Lead, flow: ConversationFlow) -> str:
    """
    Determine the qualification status based on collected data.
    Returns the updated qualification_status string.
    """
    # Check if we have all core fields
    has_intent = bool(lead.buy_or_rent)
    has_property_type = bool(lead.property_type)
    has_budget = lead.budget is not None and lead.budget > 0
    has_income = lead.income is not None and lead.income > 0
    has_urgency = bool(lead.urgency)
    has_name = bool(lead.name)

    # Count how many fields we've collected
    fields_collected = sum([has_intent, has_property_type, has_budget, has_income, has_urgency, has_name])

    if fields_collected >= 5:
        status = "qualified"
    elif fields_collected >= 2:
        status = "qualifying"
    else:
        status = "new"

    return status


def _run_affordability_if_possible(lead: Lead) -> Optional[str]:
    """
    If we have enough data, run the affordability engine.
    Returns a message snippet to include in the AI context, or None.
    """
    if lead.income and lead.budget and lead.buy_or_rent:
        result = calculate_affordability(
            income=lead.income,
            property_price=lead.budget,
            buy_or_rent=lead.buy_or_rent,
        )
        if result["affordable"]:
            # Store affordability results in lead context for the AI to use
            lead.qualification_score = 0.8
            db.session.commit()
            return (
                f"[Affordability check: The lead can afford up to ${result['max_price']:,.0f}. "
                f"They are within budget.]"
            )
        else:
            return (
                f"[Affordability check: The lead's budget of ${lead.budget:,.0f} "
                f"exceeds the affordable range of ${result['max_price']:,.0f}. "
                f"Be gentle when discussing this.]"
            )
    return None


def process_incoming_message(
    from_number: str,
    text_body: str,
) -> bool:
    """
    Process a single WhatsApp text message through the AI conversation engine.

    Args:
        from_number: The sender's phone number (as string from WhatsApp).
        text_body: The message text content.

    Returns:
        True if the message was processed and a reply sent successfully.
    """
    # ------------------------------------------------------------------
    # 1. Load / create lead and conversation
    # ------------------------------------------------------------------
    lead = _get_or_create_lead(from_number)
    conversation = _get_or_create_conversation(lead)

    # If this is a returning lead with a completed conversation, start fresh
    if conversation.session_state == "done":
        conversation.session_state = "greeting"
        conversation.messages = []
        conversation.context = {}
        db.session.commit()

    flow = ConversationFlow(lead, conversation)

    # ------------------------------------------------------------------
    # 2. Save the incoming user message
    # ------------------------------------------------------------------
    flow.add_message("user", text_body)

    # ------------------------------------------------------------------
    # 3. Build messages array for OpenAI
    # ------------------------------------------------------------------
    agency_name = current_app.config.get("AGENCY_NAME", "QualifyAI Realty")
    system_prompt = SYSTEM_PROMPT.format(agency_name=agency_name)

    # Build context from lead data + conversation history
    messages_for_ai = [{"role": "system", "content": system_prompt}]

    # Add state-specific instructions
    state = flow.state
    from app.conversation.prompts import (
        INTENT_GATHERING, QUALIFICATION, RECOMMENDATION, VIEWING_BOOKING,
    )
    state_hints = {
        ConversationState.GREETING: "",
        ConversationState.ASKING_INTENT: INTENT_GATHERING,
        ConversationState.ASKING_PROPERTY_TYPE: QUALIFICATION,
        ConversationState.ASKING_BUDGET: QUALIFICATION,
        ConversationState.ASKING_INCOME: QUALIFICATION,
        ConversationState.ASKING_URGENCY: QUALIFICATION,
        ConversationState.ASKING_NAME: QUALIFICATION,
        ConversationState.ASKING_EMAIL: QUALIFICATION,
        ConversationState.QUALIFIED: "",
        ConversationState.RECOMMENDING: RECOMMENDATION,
        ConversationState.BOOKING: VIEWING_BOOKING,
        ConversationState.AGENT_HANDOVER: "",
        ConversationState.DONE: "",
    }
    hint = state_hints.get(state, "")
    if hint:
        messages_for_ai.append({"role": "system", "content": hint})

    # Add lead context summary
    context_parts = []
    if lead.name:
        context_parts.append(f"Lead name: {lead.name}")
    if lead.buy_or_rent:
        context_parts.append(f"Looking to: {lead.buy_or_rent}")
    if lead.property_type:
        context_parts.append(f"Property type: {lead.property_type}")
    if lead.budget:
        context_parts.append(f"Budget: ${lead.budget:,.0f}")
    if lead.income:
        context_parts.append(f"Income: ${lead.income:,.0f}/year")
    if lead.urgency:
        context_parts.append(f"Urgency: {lead.urgency}")
    if lead.email:
        context_parts.append(f"Email: {lead.email}")

    if context_parts:
        context_str = "Known lead info:\n" + "\n".join(f"- {p}" for p in context_parts)
        messages_for_ai.append({"role": "system", "content": context_str})

    # Add affordability analysis if possible
    affordability_note = _run_affordability_if_possible(lead)
    if affordability_note:
        messages_for_ai.append({"role": "system", "content": affordability_note})

    # Add current state info
    messages_for_ai.append({
        "role": "system",
        "content": f"Current conversation state: {state.name}. "
                   f"Stay in character and ask ONE question at a time.",
    })

    # Add conversation history (last 20 messages for context)
    history = (conversation.messages or [])[-20:]
    for msg in history:
        messages_for_ai.append({
            "role": msg["role"],
            "content": msg["content"],
        })

    # ------------------------------------------------------------------
    # 4. Call OpenAI
    # ------------------------------------------------------------------
    api_key = current_app.config.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.error("OPENAI_API_KEY not configured")
        return False

    ai_service = AIService(api_key=api_key)

    ai_response = ai_service.chat_with_functions(
        messages=messages_for_ai,
        functions=EXTRACTION_FUNCTIONS,
        function_call="auto",
    )

    if ai_response is None:
        logger.error("AI service returned None — check API key and quota")
        return False

    reply_text, function_data = ai_response

    # ------------------------------------------------------------------
    # 5. Extract structured data from function calling
    # ------------------------------------------------------------------
    if function_data:
        _apply_extracted_data(lead, flow, function_data)

    # ------------------------------------------------------------------
    # 6. Compute qualification and scoring
    # ------------------------------------------------------------------
    new_status = _compute_qualification_status(lead, flow)
    if new_status != lead.qualification_status:
        lead.qualification_status = new_status
        db.session.commit()
        logger.info("Lead %s: qualification_status -> %s", lead.id, new_status)

    # Re-score the lead
    message_count = len(conversation.messages or [])
    lead.lead_score = score_lead(
        budget=lead.budget,
        urgency=lead.urgency,
        message_count=message_count,
        qualification_status=lead.qualification_status,
    )
    db.session.commit()
    logger.info("Lead %s: score -> %.2f", lead.id, lead.lead_score)

    # ------------------------------------------------------------------
    # 7. Handle special transitions
    # ------------------------------------------------------------------
    if function_data and function_data.get("requested_handover"):
        flow.transition_to(ConversationState.AGENT_HANDOVER)
    elif function_data and function_data.get("requested_viewing"):
        flow.transition_to(ConversationState.BOOKING)
    elif lead.qualification_status == "qualified" and state in (
        ConversationState.ASKING_EMAIL, ConversationState.QUALIFIED,
    ):
        if state == ConversationState.ASKING_EMAIL:
            flow.advance()  # moves to QUALIFIED
        # Don't auto-advance — let the AI drive the conversation naturally

    # ------------------------------------------------------------------
    # 8. Save AI response to conversation history
    # ------------------------------------------------------------------
    flow.add_message("assistant", reply_text)

    # ------------------------------------------------------------------
    # 9. Human-like delay, then send reply
    # ------------------------------------------------------------------
    human_delay(message_length=len(reply_text), complexity="medium")

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