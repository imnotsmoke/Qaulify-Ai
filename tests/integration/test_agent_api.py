import pytest
from app.models import db, Lead, Conversation

def test_list_leads(client, sample_lead):
    response = client.get("/api/agent/leads")
    assert response.status_code == 200
    assert len(response.json["leads"]) >= 1
    assert response.json["leads"][0]["phone"] == sample_lead.phone

def test_list_leads_filter(client, sample_lead):
    response = client.get("/api/agent/leads?status=qualified")
    assert response.status_code == 200
    assert len(response.json["leads"]) == 0
    
    response = client.get("/api/agent/leads?status=new")
    assert response.status_code == 200
    assert len(response.json["leads"]) >= 1

def test_get_lead(client, sample_lead, sample_conversation):
    response = client.get(f"/api/agent/leads/{sample_lead.id}")
    assert response.status_code == 200
    assert response.json["lead"]["id"] == sample_lead.id
    assert len(response.json["conversations"]) == 1

def test_takeover_conversation(client, sample_conversation):
    response = client.post(f"/api/agent/conversations/{sample_conversation.id}/takeover")
    assert response.status_code == 200
    assert response.json["session_state"] == "agent_handover"

def test_mark_follow_up(client, sample_lead):
    response = client.post(f"/api/agent/leads/{sample_lead.id}/follow-up")
    assert response.status_code == 200
    assert response.json["follow_up_sent"] is True
