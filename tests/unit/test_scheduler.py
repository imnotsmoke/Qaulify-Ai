import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from app.services.scheduler import send_follow_ups, cleanup_stale_leads
from app.models import Lead, db

def test_send_follow_ups(app):
    with app.app_context():
        # Create a lead due for follow-up
        lead = Lead(
            phone="111222333",
            qualification_status="follow_up",
            follow_up_sent=False
        )
        db.session.add(lead)
        db.session.commit()
        
        # Manually backdate updated_at since it's auto-set on commit
        # Actually, we can use timedelta in the query.
        # But for testing, we might need to manipulate the DB value.
        lead.updated_at = datetime.now(timezone.utc) - timedelta(hours=25)
        db.session.commit()
        
        send_follow_ups(app)
        
        db.session.refresh(lead)
        assert lead.follow_up_sent is True

def test_cleanup_stale_leads(app):
    with app.app_context():
        # Create a stale lead
        lead = Lead(
            phone="444555666",
            qualification_status="new"
        )
        db.session.add(lead)
        db.session.commit()
        
        lead.updated_at = datetime.now(timezone.utc) - timedelta(days=8)
        db.session.commit()
        
        cleanup_stale_leads(app)
        
        db.session.refresh(lead)
        assert lead.qualification_status == "follow_up"
