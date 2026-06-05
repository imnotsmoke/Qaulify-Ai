import pytest
from app import create_app, db
from app.models import Lead, Conversation, Property, Agent

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'OPENAI_API_KEY': 'test_key',
        'WHATSAPP_TOKEN': 'test_token',
        'WHATSAPP_PHONE_NUMBER_ID': 'test_id',
        'CALENDLY_TOKEN': 'test_calendly_token'
    })

    # Disable session expiration on commit for easier testing
    with app.app_context():
        db.session.configure(expire_on_commit=False)
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def sample_lead(app):
    with app.app_context():
        lead = Lead(
            phone="1234567890",
            name="John Doe",
            qualification_status="new"
        )
        db.session.add(lead)
        db.session.commit()
        return lead

@pytest.fixture
def sample_conversation(app, sample_lead):
    with app.app_context():
        conv = Conversation(
            lead_id=sample_lead.id,
            session_state="greeting",
            messages=[],
            context={}
        )
        db.session.add(conv)
        db.session.commit()
        return conv
