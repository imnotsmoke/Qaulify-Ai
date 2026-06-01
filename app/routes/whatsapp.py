"""
WhatsApp Cloud API webhook routes.

Handles:
- GET /webhook/whatsapp — verification challenge (Meta requires this)
- POST /webhook/whatsapp — incoming messages from WhatsApp users
"""
import logging

from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

whatsapp_bp = Blueprint("whatsapp", __name__, url_prefix="/webhook")


@whatsapp_bp.route("/whatsapp", methods=["GET"])
def verify_webhook():
    """
    WhatsApp Cloud API requires a GET endpoint for webhook verification.

    Expected query parameters:
        hub.mode     = "subscribe"
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
    Receive incoming WhatsApp messages from Meta's Cloud API.

    Expects a JSON payload with the standard WhatsApp webhook structure.
    Currently logs the incoming payload and returns acknowledgement.
    Will be expanded to process messages through the AI conversation engine.
    """
    data = request.get_json(silent=True)
    if not data:
        logger.warning("Received empty or non-JSON payload")
        return jsonify({"error": "Invalid payload"}), 400

    logger.info("Incoming WhatsApp webhook: %s", data)

    # Extract the message entry from the WhatsApp payload
    try:
        entry = data.get("entry", [])
        if not entry:
            return jsonify({"status": "ok"}), 200

        for entry_item in entry:
            changes = entry_item.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    # Extract standard WhatsApp message fields
                    from_number = msg.get("from", "unknown")
                    msg_id = msg.get("id", "")
                    msg_type = msg.get("type", "unknown")
                    text_body = ""
                    if msg_type == "text":
                        text_body = msg.get("text", {}).get("body", "")

                    logger.info(
                        "Message from %s (type=%s, id=%s): %s",
                        from_number,
                        msg_type,
                        msg_id,
                        text_body,
                    )

                    # TODO: route to AI conversation engine
                    # This will be handled by conversation/flow.py in a future sprint
    except Exception as e:
        logger.error("Error processing WhatsApp message: %s", str(e), exc_info=True)
        return jsonify({"error": "Internal processing error"}), 500

    return jsonify({"status": "ok"}), 200