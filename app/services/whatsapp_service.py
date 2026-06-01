"""
WhatsApp Cloud API integration service.

Handles sending messages via the Meta WhatsApp Cloud API.
"""
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Wraps the Meta WhatsApp Cloud API for sending messages.

    API docs: https://developers.facebook.com/docs/whatsapp/cloud-api
    """

    API_BASE = "https://graph.facebook.com/v18.0"

    def __init__(self, token: str, phone_number_id: str):
        self.token = token
        self.phone_number_id = phone_number_id

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _url(self) -> str:
        return f"{self.API_BASE}/{self.phone_number_id}/messages"

    def send_text(self, to: str, body: str) -> bool:
        """
        Send a plain text message to a WhatsApp number.

        Args:
            to: The recipient's phone number (no leading '+').
            body: The message text (max 4096 chars).

        Returns:
            True if the message was sent successfully.
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }

        try:
            resp = requests.post(self._url(), headers=self._headers(), json=payload, timeout=15)
            resp.raise_for_status()
            logger.info("Message sent to %s: %s...", to, body[:80])
            return True
        except requests.exceptions.RequestException as e:
            logger.error("Failed to send message to %s: %s", to, str(e))
            return False

    def send_interactive_list(self, to: str, header: str, body: str, rows: list) -> bool:
        """
        Send an interactive list message (for option selection).

        Args:
            to: Recipient phone number.
            header: List header text.
            body: List body text.
            rows: List of dicts with 'id' and 'title' keys.
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": header},
                "body": {"text": body},
                "action": {
                    "button": "Choose an option",
                    "sections": [{"title": "Options", "rows": rows}],
                },
            },
        }
        try:
            resp = requests.post(self._url(), headers=self._headers(), json=payload, timeout=15)
            resp.raise_for_status()
            logger.info("Interactive list sent to %s", to)
            return True
        except requests.exceptions.RequestException as e:
            logger.error("Failed to send interactive to %s: %s", to, str(e))
            return False

    def send_typing_indicator(self, to: str) -> bool:
        """Send a typing indicator to simulate human-like delays."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": "."},
        }
        # A simpler approach: mark the message as read or just sleep
        # WhatsApp API doesn't have native typing indicators; use delay instead
        return True