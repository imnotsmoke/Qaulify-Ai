"""
Human-like typing delays for WhatsApp messages.

Simulates the natural pacing of a human consultant to keep conversations
feeling warm and organic rather than robotic instant replies.
"""
import random
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Base delay ranges (in seconds)
SHORT_MESSAGE_DELAY = (0.5, 1.5)    # Quick replies like "OK", "Sure"
MEDIUM_MESSAGE_DELAY = (1.5, 3.0)   # Normal responses
LONG_MESSAGE_DELAY = (2.0, 4.0)     # Detailed explanations
COMPLEX_DELAY = (3.0, 5.0)          # Responses that require "thinking"


def human_delay(message_length: int = 0, complexity: str = "medium") -> None:
    """
    Sleep for a human-like duration based on message characteristics.

    Args:
        message_length: Number of characters in the response.
        complexity: 'short', 'medium', 'long', or 'complex'.
    """
    if complexity == "short":
        min_s, max_s = SHORT_MESSAGE_DELAY
    elif complexity == "medium":
        min_s, max_s = MEDIUM_MESSAGE_DELAY
    elif complexity == "long":
        min_s, max_s = LONG_MESSAGE_DELAY
    elif complexity == "complex":
        min_s, max_s = COMPLEX_DELAY
    else:
        min_s, max_s = MEDIUM_MESSAGE_DELAY

    # Scale by message length (longer messages take "longer to type")
    length_factor = min(message_length / 200.0, 1.0)
    scaled_min = min_s * (1.0 + length_factor * 0.5)
    scaled_max = max_s * (1.0 + length_factor * 0.5)

    delay = random.uniform(scaled_min, scaled_max)
    logger.debug("Human delay: %.2fs (complexity=%s, len=%d)", delay, complexity, message_length)
    time.sleep(delay)