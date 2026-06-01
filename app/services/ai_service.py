"""
OpenAI integration service.

Provides the interface to GPT models for:
- Natural language understanding of lead messages
- Generating conversational responses
- Extracting structured data (budget, intent, etc.) via function calling
"""
import json
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class AIService:
    """
    Wraps OpenAI chat completion calls.

    Reads the API key from config at init time (should be passed from
    ``current_app.config["OPENAI_API_KEY"]``).
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

    def chat_with_functions(
        self,
        messages: list,
        functions: Optional[list] = None,
        function_call: str = "auto",
        temperature: float = 0.7,
    ) -> Optional[Tuple[str, dict]]:
        """
        Send a chat completion request with function calling support.

        Args:
            messages: List of dicts with 'role' and 'content' keys.
            functions: List of function definitions for function calling.
            function_call: 'auto', 'none', or a specific function name.
            temperature: Sampling temperature.

        Returns:
            Tuple of (assistant_reply_text, extracted_data_dict).
            ``extracted_data_dict`` may be empty if no function was called.
            Returns None on failure.
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if functions:
            kwargs["functions"] = functions
            kwargs["function_call"] = function_call

        try:
            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            msg = choice.message

            reply_text = msg.content or ""
            extracted_data = {}

            # If the model called a function, parse the arguments
            if msg.function_call and msg.function_call.arguments:
                try:
                    extracted_data = json.loads(msg.function_call.arguments)
                    logger.debug(
                        "Function call '%s' returned: %s",
                        msg.function_call.name,
                        extracted_data,
                    )
                except json.JSONDecodeError as e:
                    logger.warning(
                        "Failed to parse function call arguments: %s", e
                    )

            return reply_text, extracted_data

        except Exception as e:
            logger.error(
                "OpenAI API call (with functions) failed: %s", str(e), exc_info=True
            )
            return None

    def extract_intent(self, message: str) -> dict:
        """
        Extract structured intent from a user message using function calling.

        Args:
            message: The user's message text.

        Returns:
            Dict with extracted fields (intent, budget, etc.).
        """
        logger.debug("extract_intent called with: %s", message)
        # This is now handled by chat_with_functions in the message handler
        return {"intent": "unknown"}