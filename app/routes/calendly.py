"""
Calendly webhook routes.

Handles:
- POST /webhook/calendly — booking events from Calendly
  (invitee.created, invitee.canceled, etc.)

When a viewing is booked or cancelled, the corresponding Lead record
is updated in the database.
"""
import logging
import hmac
import hashlib
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app

from app.models import db, Lead

logger = logging.getLogger(__name__)

calendly_bp = Blueprint("calendly", __name__, url_prefix="/webhook")


def _lookup_lead(invitee: dict) -> Lead | None:
    """
    Find a lead by email or phone from the Calendly invitee data.
    Returns None if no matching lead is found.
    """
    email = (invitee.get("email") or "").strip().lower()
    phone = (invitee.get("phone") or "").strip()

    lead = None
    if email:
        lead = Lead.query.filter_by(email=email).first()
    if not lead and phone:
        # Try different phone formats
        for fmt in [phone, phone.lstrip("+"), phone.replace(" ", ""), phone.replace("-", "")]:
            lead = Lead.query.filter_by(phone=fmt).first()
            if lead:
                break
            # Also try matching by the last 10 digits
            digits = "".join(c for c in fmt if c.isdigit())
            if len(digits) >= 10:
                lead = Lead.query.filter(Lead.phone.like(f"%{digits[-10:]}")).first()
                if lead:
                    break
    return lead


def _send_post_booking_message(lead: Lead, event_start_time: str) -> None:
    """
    Send a confirmation message to the lead after a booking is made.

    Uses the WhatsApp service to send a post-booking confirmation
    that includes the Calendly link and booking time.
    """
    from app.services.whatsapp_service import WhatsAppService
    from app.utils.templates import viewing_booked

    calendly_link = current_app.config.get("CALENDLY_LINK", "")
    wa_token = current_app.config.get("WHATSAPP_TOKEN", "")
    wa_phone_id = current_app.config.get("WHATSAPP_PHONE_NUMBER_ID", "")
    agency_name = current_app.config.get("AGENCY_NAME", "QualifyAI Realty")

    if not wa_token or not wa_phone_id:
        logger.warning("WhatsApp not configured — skipping post-booking message")
        return

    # Build confirmation message
    try:
        booked_time = datetime.fromisoformat(event_start_time.replace("Z", "+00:00"))
        time_str = booked_time.strftime("%A, %B %d at %I:%M %p")
    except (ValueError, TypeError):
        time_str = event_start_time

    name = lead.name or "there"
    body = (
        f"🎉 Viewing confirmed, {name}!\n\n"
        f"Your property viewing has been booked for **{time_str}**.\n\n"
        f"Booking link: {calendly_link}\n\n"
        f"Need to reschedule? Just let me know!\n"
        f"— {agency_name}"
    )

    wa_service = WhatsAppService(token=wa_token, phone_number_id=wa_phone_id)
    wa_service.send_text(to=lead.phone, body=body)


@calendly_bp.route("/calendly", methods=["POST"])
def handle_calendly_webhook():
    """
    Process Calendly webhook events (e.g., invitee.created).

    Verifies the webhook signature using HMAC-SHA256 (if CALENDLY_WEBHOOK_SECRET
    is configured), logs the event, and updates the corresponding Lead record.
    """
    # Verify webhook signature if secret is configured
    secret = current_app.config.get("CALENDLY_WEBHOOK_SECRET", "")
    if secret:
        signature = request.headers.get("X-Calendly-Signature", "")
        if not signature:
            logger.warning("Calendly webhook missing signature header")
            return jsonify({"error": "Missing signature"}), 401

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
        payload = data.get("payload", {})
        invitee = payload.get("invitee", {})
        event = payload.get("event", {})

        invitee_name = invitee.get("name", "")
        invitee_email = invitee.get("email", "")
        invitee_phone = invitee.get("phone", "")
        event_start_time = event.get("start_time", "")
        event_uri = event.get("uri", "")

        if event_type == "invitee.created":
            logger.info(
                "Viewing booked: %s (%s) at %s",
                invitee_name, invitee_email, event_start_time,
            )

            lead = _lookup_lead(invitee)
            if lead:
                # Update lead with booking info
                lead.viewing_booked = True
                try:
                    lead.viewing_date = datetime.fromisoformat(
                        event_start_time.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

                # Update lead score to reflect booking
                lead.lead_score = max(lead.lead_score or 0, 0.9)
                lead.qualification_status = "qualified"

                # Store email if we got it from Calendly
                if invitee_email and not lead.email:
                    lead.email = invitee_email

                db.session.commit()
                logger.info(
                    "Lead %s updated: viewing_booked=True, viewing_date=%s",
                    lead.id, lead.viewing_date,
                )

                # Send post-booking confirmation
                _send_post_booking_message(lead, event_start_time)
            else:
                logger.info(
                    "No matching lead found for %s / %s — "
                    "booking logged but lead not updated",
                    invitee_email, invitee_phone,
                )

        elif event_type == "invitee.canceled":
            logger.info(
                "Viewing cancelled: %s (%s)",
                invitee_name, invitee_email,
            )

            lead = _lookup_lead(invitee)
            if lead:
                lead.viewing_booked = False
                lead.viewing_date = None
                lead.qualification_status = "follow_up"
                db.session.commit()
                logger.info(
                    "Lead %s updated: viewing_booked=False, status=follow_up",
                    lead.id,
                )
            else:
                logger.info(
                    "No matching lead found for cancellation: %s",
                    invitee_email,
                )

        else:
            logger.info("Unhandled Calendly event type: %s", event_type)

    except Exception as e:
        logger.error("Error processing Calendly webhook: %s", str(e), exc_info=True)
        return jsonify({"error": "Internal processing error"}), 500

    return jsonify({"status": "ok"}), 200