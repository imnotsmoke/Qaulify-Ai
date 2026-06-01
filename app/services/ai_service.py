"""
OpenAI integration service.

Provides the interface to GPT models for:
- Natural language understanding of lead messages
- Generating conversational responses
- Extracting structured data (budget, intent, etc.) from free text
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AIService:
    """
    Wraps OpenAI chat completion calls.

    To be wired up in a future sprint with the conversation flow engine.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy-init the OpenAI client to avoid import-time failures."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def chat(self, messages: list, temperature: float = 0.7) -> Optional[str]:
        """
        Send a chat completion request.

        Args:
            messages: List of dicts with 'role' and 'content' keys.
            temperature: Sampling temperature (0.0 — deterministic, 1.0 — creative).

        Returns:
            The assistant's response text, or None on failure.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("OpenAI API call failed: %s", str(e), exc_info=True)
            return None

    def extract_intent(self, message: str) -> dict:
        """
        Extract structured intent from a user message.

        Placeholder — will use function-calling to extract fields like
        intent (buy/rent), budget, property_type, urgency.
        """
        # TODO: implement with OpenAI function calling
        logger.debug("extract_intent called with: %s", message)
        return {"intent": "unknown"}