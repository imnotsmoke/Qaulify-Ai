"""
Calendly webhook routes.

Handles:
- POST /webhook/calendly — booking events from Calendly
  (invitee.created, invitee.canceled, etc.)
"""
import logging
import hmac
import hashlib

from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

calendly_bp = Blueprint("calendly", __name__, url_prefix="/webhook")


@calendly_bp.route("/calendly", methods=["POST"])
def handle_calendly_webhook():
    """
    Process Calendly webhook events (e.g., invitee.created).

    Verifies the webhook signature using HMAC-SHA256 (if CALENDLY_WEBHOOK_SECRET
    is configured), logs the event, and updates the corresponding Lead record
    when a viewing is booked.
    """
    # Verify webhook signature if secret is configured
    secret = current_app.config.get("CALENDLY_WEBHOOK_SECRET", "")
    if secret:
        signature = request.headers.get("X-Calendly-Signature", "")
        if not signature:
            logger.warning("Calendly webhook missing signature header")
            return jsonify({"error": "Missing signature"}), 401

        # Compute expected signature
        payload = request.get_data(as_text=True)
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(f"sha256={expected_sig}", signature):
            logger.warning("Calendly webhook signature mismatch")
            return jsonify({"error": "Invalid signature"}), 403

    data = request.get_json(silent=True)
    if not data:
        logger.warning("Received empty or non-JSON Calendly payload")
        return jsonify({"error": "Invalid payload"}), 400

    event_type = data.get("event", "unknown")
    logger.info("Calendly webhook received: event=%s", event_type)

    try:
        if event_type == "invitee.created":
            payload = data.get("payload", {})
            invitee = payload.get("invitee", {})
            event = payload.get("event", {})

            invitee_name = invitee.get("name", "")
            invitee_email = invitee.get("email", "")
            invitee_phone = invitee.get("phone", "")
            event_start_time = event.get("start_time", "")

            logger.info(
                "Viewing booked: %s (%s) at %s",
                invitee_name,
                invitee_email,
                event_start_time,
            )

            # TODO: Match invitee to Lead record by phone/email and
            #       update viewing_booked, viewing_date fields.
            # This will be wired up once the Lead lookup service is built.

        elif event_type == "invitee.canceled":
            payload = data.get("payload", {})
            invitee = payload.get("invitee", {})
            logger.info(
                "Viewing cancelled: %s (%s)",
                invitee.get("name", ""),
                invitee.get("email", ""),
            )
            # TODO: Update Lead viewing status to cancelled

        else:
            logger.info("Unhandled Calendly event type: %s", event_type)

    except Exception as e:
        logger.error("Error processing Calendly webhook: %s", str(e), exc_info=True)
        return jsonify({"error": "Internal processing error"}), 500

    return jsonify({"status": "ok"}), 200