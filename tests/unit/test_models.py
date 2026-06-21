import pytest
from app.models import db, Lead, Conversation, Property, Agent

def test_new_lead(app):
    with app.app_context():
        lead = Lead(phone="+1234567890", name="Test User")
        db.session.add(lead)
        db.session.commit()
        
        assert lead.id is not None
        assert lead.phone == "+1234567890"
        assert lead.qualification_status == "new"
        assert lead.created_at is not None

def test_lead_to_dict(app, sample_lead):
    with app.app_context():
        # Need to refresh or merge sample_lead into current session
        lead = db.session.merge(sample_lead)
        d = lead.to_dict()
        assert d["phone"] == "1234567890"
        assert d["name"] == "John Doe"
        assert "id" in d

def test_property_creation(app):
    with app.app_context():
        prop = Property(
            title="Sunny Apartment",
            type="rent",
            price=1500.0,
            location="Malta"
        )
        db.session.add(prop)
        db.session.commit()
        
        assert prop.id is not None
        assert prop.price == 1500.0

def test_conversation_relationship(app, sample_lead):
    with app.app_context():
        lead = db.session.merge(sample_lead)
        conv = Conversation(lead_id=lead.id, session_state="greeting")
        db.session.add(conv)
        db.session.commit()
        
        assert len(lead.conversations.all()) == 1
        assert lead.conversations.first().session_state == "greeting"
