import json
import pytest
from unittest.mock import patch, MagicMock

def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json["status"] == "ok"

def test_whatsapp_verify_success(client, app):
    with app.app_context():
        # Mock config
        app.config["WHATSAPP_VERIFY_TOKEN"] = "my_token"
        
        response = client.get("/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=my_token&hub.challenge=1234")
        assert response.status_code == 200
        assert response.data.decode() == "1234"

def test_whatsapp_verify_fail(client, app):
    with app.app_context():
        app.config["WHATSAPP_VERIFY_TOKEN"] = "my_token"
        
        response = client.get("/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=1234")
        assert response.status_code == 403

@patch("app.routes.whatsapp.process_incoming_message")
def test_whatsapp_webhook_post(mock_process, client):
    mock_process.return_value = True
    
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "1234567890",
                        "type": "text",
                        "text": {"body": "I want to buy a house"}
                    }]
                }
            }]
        }]
    }
    
    response = client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200
    mock_process.assert_called_once_with(from_number="1234567890", text_body="I want to buy a house")

def test_calendly_webhook(client, app, sample_lead):
    # Need to make sure the lead exists in the DB for the webhook to find it
    payload = {
        "event": "invitee.created",
        "payload": {
            "invitee": {
                "email": "test@example.com",
                "phone": "1234567890"
            },
            "event": {
                "start_time": "2024-06-10T10:00:00Z"
            }
        }
    }
    
    # Verification will skip because CALENDLY_WEBHOOK_SECRET is empty in test
    with app.app_context():
        from app.models import Lead, db
        lead = db.session.merge(sample_lead)
        lead.phone = "1234567890"
        db.session.commit()
        
    response = client.post("/webhook/calendly", json=payload)
    assert response.status_code == 200
    
    # Check if lead status updated
    with app.app_context():
        from app.models import Lead, db
        lead = Lead.query.filter_by(phone="1234567890").first()
        assert lead.viewing_booked is True
        assert lead.qualification_status == "qualified"
