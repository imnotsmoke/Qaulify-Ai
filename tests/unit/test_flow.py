import pytest
from app.conversation.flow import ConversationFlow, ConversationState
from app.models import Lead, Conversation, db

def test_flow_initial_state(app, sample_lead, sample_conversation):
    with app.app_context():
        lead = db.session.merge(sample_lead)
        conv = db.session.merge(sample_conversation)
        flow = ConversationFlow(lead, conv)
        assert flow.state == ConversationState.GREETING

def test_flow_transition(app, sample_lead, sample_conversation):
    with app.app_context():
        lead = db.session.merge(sample_lead)
        conv = db.session.merge(sample_conversation)
        flow = ConversationFlow(lead, conv)
        
        flow.transition_to(ConversationState.ASKING_INTENT)
        assert flow.state == ConversationState.ASKING_INTENT
        
        # Check database persistence
        db.session.refresh(conv)
        assert conv.session_state == "asking_intent"

def test_flow_advance(app, sample_lead, sample_conversation):
    with app.app_context():
        lead = db.session.merge(sample_lead)
        conv = db.session.merge(sample_conversation)
        flow = ConversationFlow(lead, conv)
        
        next_state = flow.advance()
        assert next_state == ConversationState.ASKING_INTENT
        assert flow.state == ConversationState.ASKING_INTENT

def test_flow_add_message(app, sample_lead, sample_conversation):
    with app.app_context():
        lead = db.session.merge(sample_lead)
        conv = db.session.merge(sample_conversation)
        flow = ConversationFlow(lead, conv)
        
        flow.add_message("user", "Hello")
        assert len(conv.messages) == 1
        assert conv.messages[0]["role"] == "user"
        assert conv.messages[0]["content"] == "Hello"

def test_flow_update_context(app, sample_lead, sample_conversation):
    with app.app_context():
        lead = db.session.merge(sample_lead)
        conv = db.session.merge(sample_conversation)
        flow = ConversationFlow(lead, conv)
        
        flow.update_context("budget_max", 500000)
        assert conv.context["budget_max"] == 500000
