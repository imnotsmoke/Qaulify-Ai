"""
Conversation state machine.

Manages the progression of a WhatsApp conversation through defined states:
greeting -> asking_intent -> qualifying -> recommending -> booking -> done

Each state has an entry action and transition rules.
"""
import logging
from enum import Enum, auto
from typing import Optional

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
    # Agent handover can happen from most states
}


class ConversationFlow:
    """
    Encapsulates the conversation flow for a single lead.

    This is the core orchestration layer that will be wired to:
    - AIService for generating responses
    - WhatsAppService for sending messages
    - Lead/Conversation models for persistence
    """

    def __init__(self, lead: Lead, conversation: Conversation):
        self.lead = lead
        self.conversation = conversation

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

    def add_message(self, role: str, content: str) -> None:
        """Append a message to the conversation history."""
        from datetime import datetime, timezone
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

    def can_handover(self) -> bool:
        """Check if the conversation is in a state where handover makes sense."""
        return self.state in (
            ConversationState.RECOMMENDING,
            ConversationState.BOOKING,
            ConversationState.QUALIFIED,
        )