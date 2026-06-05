import pytest
from unittest.mock import MagicMock, patch
from app.services.ai_service import AIService

def test_ai_service_chat():
    service = AIService(api_key="test_key")
    
    with patch("openai.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello from AI"
        mock_client.chat.completions.create.return_value = mock_response
        
        reply = service.chat([{"role": "user", "content": "Hi"}])
        
        assert reply == "Hello from AI"
        mock_client.chat.completions.create.assert_called_once()

def test_ai_service_chat_with_functions():
    service = AIService(api_key="test_key")
    
    with patch("openai.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "AI Reply"
        mock_msg.function_call.name = "extract_data"
        mock_msg.function_call.arguments = '{"budget": 500000}'
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = mock_msg
        mock_client.chat.completions.create.return_value = mock_response
        
        reply, data = service.chat_with_functions(
            messages=[{"role": "user", "content": "My budget is 500k"}],
            functions=[{"name": "extract_data", "parameters": {}}]
        )
        
        assert reply == "AI Reply"
        assert data == {"budget": 500000}

def test_ai_service_failure():
    service = AIService(api_key="test_key")
    
    with patch("openai.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        reply = service.chat([{"role": "user", "content": "Hi"}])
        assert reply is None
