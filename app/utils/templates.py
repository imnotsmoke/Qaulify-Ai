"""
Message templates for the AI Property Consultant.

All user-facing messages are centralised here for consistency and easy
customisation (e.g., changing agency name or tone).
"""
from typing import Optional

# --- Greeting messages ---

GREETING_NEW = (
    "👋 Hi! I'm the AI Property Consultant from {agency_name}.\n\n"
    "I'm here to help you find your perfect property. "
    "Let me ask you a few quick questions to get started!\n\n"
    "Are you looking to **buy** or **rent**?"
)

GREETING_RETURNING = (
    "Welcome back! 👋 Great to hear from you again.\n\n"
    "Last time we spoke, you were looking to {goal}. "
    "Would you like to pick up where we left off?"
)

# --- Qualification questions ---

ASK_INTENT = "Are you looking to **buy** or **rent**?"
ASK_PROPERTY_TYPE = "What type of property are you looking for? (e.g., apartment, house, townhouse, studio)"
ASK_BUDGET = "What's your approximate budget?"
ASK_INCOME = "Roughly, what's your annual household income? (This helps me check affordability!)"
ASK_URGENCY = "How soon are you looking to move?"
ASK_NAME = "Great! What's your name?"
ASK_EMAIL = "And your email address, so I can send you property suggestions?"

# --- Responses ---

QUALIFIED_RESPONSE = (
    "Wonderful, {name}! 🎉 You're a great fit for what we have available.\n\n"
    "Would you like to **book a viewing** for one of our properties?"
)

DISQUALIFIED_RESPONSE = (
    "Thank you for your interest, {name}! Based on what you've shared, "
    "we don't currently have properties that match your criteria. "
    "I'll keep you in mind if something suitable comes up!"
)

VIEWING_BOOKED = (
    "Perfect! You're all set. 🎉\n\n"
    "Here's a link to book your preferred viewing time:\n"
    "{calendly_link}\n\n"
    "Feel free to pick a slot that works best for you!"
)

FOLLOW_UP = (
    "Hi {name}! 👋 Just checking in — are you still looking for a property? "
    "We have some new listings that might interest you!"
)

AGENT_HANDOVER = (
    "Let me connect you with one of our agents who can help you further. "
    "One moment please... 🫡"
)

# --- Error / fallback ---

UNKNOWN_COMMAND = (
    "I'm not sure I understood that. Could you rephrase?\n\n"
    "Here's what I can help with:\n"
    "• Finding properties to buy or rent\n"
    "• Checking affordability\n"
    "• Booking viewings"
)


def greeting_new(agency_name: str = "QualifyAI Realty") -> str:
    """Generate a new-lead greeting."""
    return GREETING_NEW.format(agency_name=agency_name)


def greeting_returning(goal: str) -> str:
    """Generate a returning-lead greeting."""
    return GREETING_RETURNING.format(goal=goal)


def qualified_response(name: str) -> str:
    return QUALIFIED_RESPONSE.format(name=name)


def disqualified_response(name: str) -> str:
    return DISQUALIFIED_RESPONSE.format(name=name)


def viewing_booked(calendly_link: str) -> str:
    return VIEWING_BOOKED.format(calendly_link=calendly_link)


def follow_up(name: str) -> str:
    return FOLLOW_UP.format(name=name)