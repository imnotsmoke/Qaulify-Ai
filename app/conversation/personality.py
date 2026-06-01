"""
Personality engine.

Defines the tone, style, and behavioural rules for the AI Property Consultant.

This module provides configurable knobs for:
- Formality level (casual ↔ formal)
- Emoji usage frequency
- Response verbosity
- Proactiveness (how often to offer suggestions without being asked)
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class PersonalityConfig:
    """Configuration knobs for the AI's conversational personality."""

    name: str = "QualifyAI Assistant"
    formality: float = 0.5          # 0.0 = very casual, 1.0 = very formal
    emoji_frequency: float = 0.3    # 0.0 = no emojis, 1.0 = emojis everywhere
    verbosity: float = 0.5          # 0.0 = very brief, 1.0 = very detailed
    proactiveness: float = 0.6      # 0.0 = reactive only, 1.0 = proactive suggesting

    def formality_label(self) -> str:
        """Return a human-readable formality level for prompt construction."""
        if self.formality < 0.3:
            return "casual"
        elif self.formality < 0.7:
            return "professional"
        else:
            return "formal"

    def verbosity_label(self) -> str:
        if self.verbosity < 0.3:
            return "concise"
        elif self.verbosity < 0.7:
            return "balanced"
        else:
            return "detailed"


# Default personality — professional but friendly
DEFAULT_PERSONALITY = PersonalityConfig()

# More casual variant for younger demographics / rentals
CASUAL_PERSONALITY = PersonalityConfig(
    formality=0.2,
    emoji_frequency=0.6,
    verbosity=0.4,
    proactiveness=0.7,
)

# Formal variant for high-value / luxury clients
FORMAL_PERSONALITY = PersonalityConfig(
    formality=0.9,
    emoji_frequency=0.1,
    verbosity=0.7,
    proactiveness=0.4,
)


def get_personality_prompt(config: PersonalityConfig) -> str:
    """
    Generate a personality-injecting prompt snippet to append to the system prompt.

    Args:
        config: The desired personality configuration.

    Returns:
        A string to append to the system prompt.
    """
    return (
        f"Tone: {config.formality_label()}, {config.verbosity_label()}. "
        f"Emoji usage: {'frequent' if config.emoji_frequency > 0.5 else 'occasional' if config.emoji_frequency > 0.2 else 'minimal'}. "
        f"{'Be proactive in suggesting options and next steps.' if config.proactiveness > 0.5 else 'Wait for the lead to ask before making suggestions.'}"
    )