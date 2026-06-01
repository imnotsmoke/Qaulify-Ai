"""
APScheduler task definitions.

Handles recurring background jobs:
- Follow-up message dispatch for leads in 'follow_up' status
- Lead re-engagement checks
- Expired viewing cleanup
"""
import logging
from datetime import datetime, timezone, timedelta

from flask import Flask
from app.models import db, Lead

logger = logging.getLogger(__name__)


def schedule_jobs(app: Flask) -> None:
    """
    Register all recurring jobs with the application's APScheduler instance.

    Call this during app startup after the scheduler is initialised.
    """
    scheduler = app.scheduler

    # Check for follow-ups every hour
    scheduler.add_job(
        func=lambda: send_follow_ups(app),
        trigger="interval",
        hours=1,
        id="send_follow_ups",
        name="Send follow-up messages to stale leads",
        replace_existing=True,
    )

    # Clean up stale conversations daily
    scheduler.add_job(
        func=lambda: cleanup_stale_leads(app),
        trigger="interval",
        hours=24,
        id="cleanup_stale_leads",
        name="Clean up stale / expired leads",
        replace_existing=True,
    )

    logger.info("Scheduled background jobs registered")


def send_follow_ups(app: Flask) -> None:
    """
    Send follow-up messages to leads who have been idle.

    Leads with qualification_status='follow_up' who haven't received
    a follow-up in the last 24 hours get an automated check-in message.
    """
    with app.app_context():
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        leads = Lead.query.filter(
            Lead.qualification_status == "follow_up",
            Lead.follow_up_sent == False,
            Lead.updated_at <= cutoff,
        ).all()

        logger.info("Found %d leads due for follow-up", len(leads))

        for lead in leads:
            try:
                # TODO: Send WhatsApp message via WhatsAppService
                lead.follow_up_sent = True
                db.session.commit()
                logger.info("Follow-up dispatched for lead %s", lead.id)
            except Exception as e:
                logger.error("Failed to send follow-up for lead %s: %s", lead.id, str(e))
                db.session.rollback()


def cleanup_stale_leads(app: Flask) -> None:
    """
    Archive or mark leads that have been inactive for > 7 days.
    """
    with app.app_context():
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stale = Lead.query.filter(
            Lead.updated_at <= cutoff,
            Lead.qualification_status.in_(["new", "qualifying"]),
        ).all()

        logger.info("Found %d stale leads to clean up", len(stale))

        for lead in stale:
            lead.qualification_status = "follow_up"
            db.session.commit()
            logger.info("Lead %s moved to follow_up (stale)", lead.id)