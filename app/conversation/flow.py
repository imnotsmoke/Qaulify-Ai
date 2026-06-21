"""
Conversation state machine.

Manages the progression of a WhatsApp conversation through defined states:
greeting -> asking_intent -> qualifying -> recommending -> booking -> done

Each state has an entry action and transition rules.
"""
import logging
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Optional

from flask import current_app

from app.models import db, Lead, Conversation

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """Valid states for a conversation session."""

    GREETING = auto()
    ASKING_INTENT = auto()
    ASKING_PROPERTY_TYPE = auto()
    ASKING_BUDGET = auto()
    ASKING_INCOME = auto()
    ASKING_URGENCY = auto()
    ASKING_NAME = auto()
    ASKING_EMAIL = auto()
    QUALIFIED = auto()
    RECOMMENDING = auto()
    BOOKING = auto()
    AGENT_HANDOVER = auto()
    DONE = auto()


STATE_TRANSITIONS = {
    ConversationState.GREETING: ConversationState.ASKING_INTENT,
    ConversationState.ASKING_INTENT: ConversationState.ASKING_PROPERTY_TYPE,
    ConversationState.ASKING_PROPERTY_TYPE: ConversationState.ASKING_BUDGET,
    ConversationState.ASKING_BUDGET: ConversationState.ASKING_INCOME,
    ConversationState.ASKING_INCOME: ConversationState.ASKING_URGENCY,
    ConversationState.ASKING_URGENCY: ConversationState.ASKING_NAME,
    ConversationState.ASKING_NAME: ConversationState.ASKING_EMAIL,
    ConversationState.ASKING_EMAIL: ConversationState.QUALIFIED,
    ConversationState.QUALIFIED: ConversationState.RECOMMENDING,
    ConversationState.RECOMMENDING: ConversationState.BOOKING,
    ConversationState.BOOKING: ConversationState.DONE,
}

# State-specific instruction snippets for the AI
STATE_HINTS = {
    ConversationState.GREETING: "",
    ConversationState.ASKING_INTENT: (
        "Focus on determining whether the lead wants to buy or rent. "
        "Ask one clear question and wait for their response."
    ),
    ConversationState.ASKING_PROPERTY_TYPE: (
        "You are now qualifying the lead. Collect: property_type, budget, income, and urgency. "
        "Ask one question at a time. Confirm each answer before moving to the next."
    ),
    ConversationState.ASKING_BUDGET: (
        "You are now qualifying the lead. Collect: property_type, budget, income, and urgency. "
        "Ask one question at a time. Confirm each answer before moving to the next."
    ),
    ConversationState.ASKING_INCOME: (
        "You are now qualifying the lead. Collect: property_type, budget, income, and urgency. "
        "Ask one question at a time. Confirm each answer before moving to the next."
    ),
    ConversationState.ASKING_URGENCY: (
        "You are now qualifying the lead. Collect: property_type, budget, income, and urgency. "
        "Ask one question at a time. Confirm each answer before moving to the next."
    ),
    ConversationState.ASKING_NAME: (
        "You are now qualifying the lead. Collect: property_type, budget, income, and urgency. "
        "Ask one question at a time. Confirm each answer before moving to the next."
    ),
    ConversationState.ASKING_EMAIL: (
        "You are now qualifying the lead. Collect: property_type, budget, income, and urgency. "
        "Ask one question at a time. Confirm each answer before moving to the next."
    ),
    ConversationState.QUALIFIED: "",
    ConversationState.RECOMMENDING: (
        "Based on the lead's preferences, recommend properties from the available catalogue. "
        "If no properties match, explain politely and offer alternatives."
    ),
    ConversationState.BOOKING: (
        "The lead is ready to book a viewing. Provide the Calendly booking link "
        "and encourage them to pick a convenient time slot. "
        "After they confirm a booking, ask for their email to send a confirmation."
    ),
    ConversationState.AGENT_HANDOVER: "",
    ConversationState.DONE: "",
}

# OpenAI function definition for structured data extraction
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


class ConversationFlow:
    """
    Encapsulates the conversation flow for a single lead.

    Manages the full lifecycle: storing messages, tracking state,
    building AI prompts, extracting data, computing scores,
    and orchestrating transitions.
    """

    def __init__(self, lead: Lead, conversation: Conversation):
        self.lead = lead
        self.conversation = conversation

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    @property
    def state(self) -> ConversationState:
        """Get the current conversation state."""
        state_str = self.conversation.session_state or "greeting"
        try:
            return ConversationState[state_str.upper()]
        except KeyError:
            return ConversationState.GREETING

    @state.setter
    def state(self, new_state: ConversationState) -> None:
        """Set and persist the conversation state."""
        self.conversation.session_state = new_state.name.lower()
        db.session.commit()

    def transition_to(self, target: ConversationState) -> bool:
        """Attempt to transition to a new state."""
        self.state = target
        logger.debug(
            "Conversation %s: state -> %s",
            self.conversation.id,
            target.name,
        )
        return True

    def advance(self) -> Optional[ConversationState]:
        """
        Move to the next logical state in the flow.

        Returns the new state, or None if already at a terminal state.
        """
        current = self.state
        next_state = STATE_TRANSITIONS.get(current)

        if next_state:
            self.transition_to(next_state)
            return next_state

        logger.debug("No transition defined from state %s", current.name)
        return None

    def can_handover(self) -> bool:
        """Check if the conversation is in a state where handover makes sense."""
        return self.state in (
            ConversationState.RECOMMENDING,
            ConversationState.BOOKING,
            ConversationState.QUALIFIED,
        )

    # ------------------------------------------------------------------
    # Message and context management
    # ------------------------------------------------------------------

    def add_message(self, role: str, content: str) -> None:
        """Append a message to the conversation history."""
        messages = self.conversation.messages or []
        messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.conversation.messages = messages
        db.session.commit()

    def update_context(self, key: str, value: object) -> None:
        """Store a key-value pair in the conversation context."""
        context = self.conversation.context or {}
        context[key] = value
        self.conversation.context = context
        db.session.commit()

    # ------------------------------------------------------------------
    # Lead data extraction from function call results
    # ------------------------------------------------------------------

    def apply_extracted_data(self, data: dict) -> None:
        """
        Update the lead model and conversation context with data extracted
        from the AI response via function calling.
        """
        changed = False

        for field, extract_key in [
            ("buy_or_rent", "buy_or_rent"),
            ("property_type", "property_type"),
            ("urgency", "urgency"),
            ("name", "name"),
            ("email", "email"),
        ]:
            val = data.get(extract_key)
            if val and not getattr(self.lead, field):
                setattr(self.lead, field, val)
                self.update_context(field, val)
                changed = True
                logger.info("Lead %s: %s -> %s", self.lead.id, field, val)

        for field, extract_key in [
            ("budget", "budget"),
            ("income", "income"),
        ]:
            val = data.get(extract_key)
            if val is not None and getattr(self.lead, field) is None:
                setattr(self.lead, field, val)
                self.update_context(field, val)
                changed = True
                logger.info("Lead %s: %s -> %s", self.lead.id, field, val)

        if data.get("requested_handover"):
            self.update_context("requested_handover", True)
            logger.info("Lead %s: requested handover", self.lead.id)

        if data.get("requested_viewing"):
            self.lead.viewing_requested = True
            self.update_context("requested_viewing", True)
            changed = True
            logger.info("Lead %s: requested viewing", self.lead.id)

        if changed:
            db.session.commit()

    # ------------------------------------------------------------------
    # Qualification and scoring
    # ------------------------------------------------------------------

    def compute_qualification_status(self) -> str:
        """Determine the qualification status based on collected fields."""
        checks = [
            bool(self.lead.buy_or_rent),
            bool(self.lead.property_type),
            self.lead.budget is not None and self.lead.budget > 0,
            self.lead.income is not None and self.lead.income > 0,
            bool(self.lead.urgency),
            bool(self.lead.name),
        ]
        fields_collected = sum(checks)

        if fields_collected >= 5:
            return "qualified"
        elif fields_collected >= 2:
            return "qualifying"
        return "new"

    def compute_lead_score(self) -> float:
        """Compute and store the lead's score."""
        from app.services.lead_scoring import score_lead
        message_count = len(self.conversation.messages or [])
        score = score_lead(
            budget=self.lead.budget,
            urgency=self.lead.urgency,
            message_count=message_count,
            qualification_status=self.lead.qualification_status,
        )
        self.lead.lead_score = score
        db.session.commit()
        logger.info("Lead %s: score -> %.2f", self.lead.id, score)
        return score

    def _build_affordability_note(self) -> Optional[str]:
        """Run affordability engine and return a context note for the AI."""
        if not (self.lead.income and self.lead.budget and self.lead.buy_or_rent):
            return None
        from app.services.affordability import calculate_affordability
        result = calculate_affordability(
            income=self.lead.income,
            property_price=self.lead.budget,
            buy_or_rent=self.lead.buy_or_rent,
        )
        if result["affordable"]:
            self.lead.qualification_score = 0.8
            db.session.commit()
            return (
                f"[Affordability: lead can afford up to ${result['max_price']:,.0f}. "
                f"Within budget.]"
            )
        return (
            f"[Affordability: budget ${self.lead.budget:,.0f} exceeds max "
            f"affordable ${result['max_price']:,.0f}. Be gentle.]"
        )

    # ------------------------------------------------------------------
    # AI prompt assembly
    # ------------------------------------------------------------------

    def build_ai_messages(self) -> list:
        """
        Build the full messages array for the OpenAI API call.

        Includes: system prompt, state hints, lead context,
        affordability notes, and conversation history.
        """
        from app.conversation.prompts import SYSTEM_PROMPT

        agency_name = current_app.config.get("AGENCY_NAME", "QualifyAI Realty")
        messages = [{"role": "system", "content": SYSTEM_PROMPT.format(agency_name=agency_name)}]

        # State hint
        hint = STATE_HINTS.get(self.state, "")
        if hint:
            messages.append({"role": "system", "content": hint})

        # Lead context
        context_parts = []
        field_map = [
            ("name", "Lead name: {v}"),
            ("buy_or_rent", "Looking to: {v}"),
            ("property_type", "Property type: {v}"),
            ("budget", "Budget: ${v:,.0f}"),
            ("income", "Income: ${v:,.0f}/year"),
            ("urgency", "Urgency: {v}"),
            ("email", "Email: {v}"),
        ]
        for attr, template in field_map:
            val = getattr(self.lead, attr, None)
            if val:
                context_parts.append(f"- {template.format(v=val)}")

        if context_parts:
            messages.append({
                "role": "system",
                "content": "Known lead info:\n" + "\n".join(context_parts),
            })

        # Affordability note
        note = self._build_affordability_note()
        if note:
            messages.append({"role": "system", "content": note})

        # Calendly booking link (especially relevant in BOOKING state)
        if self.state == ConversationState.BOOKING:
            calendly_link = current_app.config.get("CALENDLY_LINK", "")
            if calendly_link:
                messages.append({
                    "role": "system",
                    "content": f"The Calendly booking link is: {calendly_link}. "
                               f"Share this with the lead so they can book a viewing.",
                })

        # State reminder
        messages.append({
            "role": "system",
            "content": f"Current state: {self.state.name}. Ask ONE question at a time.",
        })

        # Conversation history (last 20)
        history = (self.conversation.messages or [])[-20:]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        return messages

    # ------------------------------------------------------------------
    # State transition logic based on extracted data
    # ------------------------------------------------------------------

    def handle_extracted_data(self, data: dict) -> None:
        """
        Apply extracted data and evaluate state transitions.
        """
        self.apply_extracted_data(data)

        # Update qualification status
        new_status = self.compute_qualification_status()
        if new_status != self.lead.qualification_status:
            self.lead.qualification_status = new_status
            db.session.commit()
            logger.info("Lead %s: status -> %s", self.lead.id, new_status)

        # Re-score
        self.compute_lead_score()

        # Handle special transitions
        if data.get("requested_handover"):
            self.transition_to(ConversationState.AGENT_HANDOVER)
        elif data.get("requested_viewing"):
            self.transition_to(ConversationState.BOOKING)
        elif (self.lead.qualification_status == "qualified"
              and self.state == ConversationState.ASKING_EMAIL):
            self.advance()

        # If we were in BOOKING state and now have the email, wrap up
        if (self.state == ConversationState.BOOKING
                and self.lead.email
                and self.lead.viewing_requested):
            self.transition_to(ConversationState.DONE)
            logger.info("Lead %s: booking complete — state -> DONE", self.lead.id)