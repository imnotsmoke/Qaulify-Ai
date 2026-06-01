"""
WhatsApp Cloud API webhook routes.

Handles:
- GET /webhook/whatsapp — verification challenge (Meta requires this)
- POST /webhook/whatsapp — incoming messages from WhatsApp users,
  routed through the AI conversation engine
"""
import logging

from flask import Blueprint, request, jsonify, current_app

from app.services.message_handler import process_incoming_message

logger = logging.getLogger(__name__)

whatsapp_bp = Blueprint("whatsapp", __name__, url_prefix="/webhook")


@whatsapp_bp.route("/whatsapp", methods=["GET"])
def verify_webhook():
    """
    WhatsApp Cloud API requires a GET endpoint for webhook verification.

    Expected query parameters:
        hub.mode         = "subscribe"
        hub.verify_token = <WHATSAPP_VERIFY_TOKEN>
        hub.challenge    = <challenge string to echo back>

    Returns 200 with the challenge string on success, 403 otherwise.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    expected_token = current_app.config.get("WHATSAPP_VERIFY_TOKEN", "")

    logger.info("Webhook verification: mode=%s, token_provided=%s", mode, bool(token))

    if mode == "subscribe" and token == expected_token:
        logger.info("Webhook verified successfully")
        return challenge, 200
    else:
        logger.warning("Webhook verification failed — token mismatch")
        return jsonify({"error": "Verification failed"}), 403


@whatsapp_bp.route("/whatsapp", methods=["POST"])
def handle_incoming():
    """
    Receive incoming WhatsApp messages from Meta's Cloud API
    and process them through the AI conversation engine.

    Expects a JSON payload with the standard WhatsApp webhook structure.
    For each text message found, it looks up or creates a Lead,
    runs the AI conversation flow, and sends a reply.
    """
    data = request.get_json(silent=True)
    if not data:
        logger.warning("Received empty or non-JSON payload")
        return jsonify({"error": "Invalid payload"}), 400

    logger.debug("Incoming WhatsApp webhook payload received")

    # ------------------------------------------------------------------
    # Meta sends a statuses array for message delivery receipts —
    # we can ignore those.
    # ------------------------------------------------------------------
    try:
        entry = data.get("entry", [])
        if not entry:
            return jsonify({"status": "ok"}), 200

        for entry_item in entry:
            changes = entry_item.get("changes", [])
            for change in changes:
                value = change.get("value", {})

                # Skip status updates (delivery receipts etc.)
                if value.get("statuses"):
                    continue

                messages = value.get("messages", [])
                for msg in messages:
                    msg_type = msg.get("type", "unknown")

                    # Only handle text messages for now
                    if msg_type != "text":
                        logger.info("Skipping non-text message type: %s", msg_type)
                        continue

                    from_number = msg.get("from", "")
                    text_body = msg.get("text", {}).get("body", "")

                    if not from_number or not text_body:
                        logger.warning("Missing from_number or text_body in message")
                        continue

                    logger.info(
                        "Processing message from %s: %.120s",
                        from_number,
                        text_body,
                    )

                    # Process through the AI conversation engine
                    try:
                        process_incoming_message(
                            from_number=from_number,
                            text_body=text_body,
                        )
                    except Exception as e:
                        logger.error(
                            "Error processing message from %s: %s",
                            from_number,
                            str(e),
                            exc_info=True,
                        )
                        # Don't return 500 to Meta — they'll retry.
                        # Log and continue.

    except Exception as e:
        logger.error("Error parsing WhatsApp payload: %s", str(e), exc_info=True)

    # Always return 200 to acknowledge receipt (WhatsApp expects this)
    return jsonify({"status": "ok"}), 200