import pytest
from unittest.mock import patch, MagicMock
from app.services.message_handler import process_incoming_message
from app.models import Lead, Conversation, db

@patch("app.services.message_handler.AIService")
@patch("app.services.message_handler.WhatsAppService")
@patch("app.services.message_handler.human_delay")
def test_full_pipeline_new_lead(mock_delay, mock_wa, mock_ai, app):
    # Mock AI response
    mock_ai_instance = mock_ai.return_value
    mock_ai_instance.chat_with_functions.return_value = (
        "Hello! I can help you with that. Are you looking to buy or rent?",
        {"intent": "greeting"}
    )
    
    # Mock WA response
    mock_wa_instance = mock_wa.return_value
    mock_wa_instance.send_text.return_value = True
    
    with app.app_context():
        success = process_incoming_message("9876543210", "Hi, I'm looking for a house")
        
        assert success is True
        
        # Verify lead created
        lead = Lead.query.filter_by(phone="9876543210").first()
        assert lead is not None
        assert lead.qualification_status == "new"
        
        # Verify conversation created
        conv = Conversation.query.filter_by(lead_id=lead.id).first()
        assert conv is not None
        assert len(conv.messages) == 2 # User + Assistant
        assert conv.messages[0]["content"] == "Hi, I'm looking for a house"
        assert conv.messages[1]["content"] == "Hello! I can help you with that. Are you looking to buy or rent?"

@patch("app.services.message_handler.AIService")
@patch("app.services.message_handler.WhatsAppService")
def test_full_pipeline_data_extraction(mock_wa, mock_ai, app, sample_lead, sample_conversation):
    mock_ai_instance = mock_ai.return_value
    mock_ai_instance.chat_with_functions.return_value = (
        "Got it, a budget of $500,000 for buying.",
        {"budget": 500000, "buy_or_rent": "buy", "intent": "providing_budget"}
    )
    
    # Mock WA response
    mock_wa_instance = mock_wa.return_value
    mock_wa_instance.send_text.return_value = True
    
    with app.app_context():
        # Ensure sample_lead is in the current session
        lead = db.session.merge(sample_lead)
        
        success = process_incoming_message(lead.phone, "My budget is 500k and I want to buy")
        
        assert success is True
        db.session.refresh(lead)
        assert lead.budget == 500000
        assert lead.buy_or_rent == "buy"
