import pytest
import requests
from unittest.mock import patch, MagicMock
from app.services.whatsapp_service import WhatsAppService

def test_whatsapp_send_text_success():
    service = WhatsAppService(token="token", phone_number_id="id")
    
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        
        success = service.send_text("123456789", "Hello")
        
        assert success is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["to"] == "123456789"
        assert kwargs["json"]["text"]["body"] == "Hello"

def test_whatsapp_send_text_failure():
    service = WhatsAppService(token="token", phone_number_id="id")
    
    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.HTTPError("Error")
        
        success = service.send_text("123456789", "Hello")
        
        assert success is False
