"""Tests for WhatsApp webhook functionality."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from clinicai.app.main import app
from clinicai.app.whatsapp import WhatsAppClient


class TestWebhookEndpoints:
    """Test WhatsApp webhook endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_webhook_verification_success(self, client):
        """Test successful webhook verification."""
        with patch('clinicai.app.whatsapp.verify_webhook_token', return_value=True):
            response = client.get(
                "/webhook/whatsapp",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "test_token",
                    "hub.challenge": "test_challenge_123"
                }
            )
            
            assert response.status_code == 200
            assert response.text == "test_challenge_123"

    def test_webhook_verification_invalid_mode(self, client):
        """Test webhook verification with invalid mode."""
        response = client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "invalid_mode",
                "hub.verify_token": "test_token",
                "hub.challenge": "test_challenge_123"
            }
        )
        
        assert response.status_code == 400

    def test_webhook_verification_invalid_token(self, client):
        """Test webhook verification with invalid token."""
        with patch('clinicai.app.whatsapp.verify_webhook_token', return_value=False):
            response = client.get(
                "/webhook/whatsapp",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "invalid_token",
                    "hub.challenge": "test_challenge_123"
                }
            )
            
            assert response.status_code == 403

    def test_webhook_message_handling(self, client):
        """Test webhook message handling."""
        # Sample WhatsApp webhook payload
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "12345",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "5511999999999",
                                    "phone_number_id": "12345"
                                },
                                "contacts": [
                                    {
                                        "profile": {"name": "Test User"},
                                        "wa_id": "5511888888888"
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "5511888888888",
                                        "id": "wamid.test123",
                                        "timestamp": "1673456789",
                                        "text": {"body": "Olá, estou com dor de cabeça"},
                                        "type": "text"
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        
        with patch('clinicai.app.graph.workflow.process_whatsapp_message') as mock_process:
            mock_process.return_value = {
                "success": True,
                "status": "open",
                "emergency": False,
                "response_sent": True,
                "phone_hash": "test_hash"
            }
            
            with patch('clinicai.app.whatsapp.whatsapp_client.mark_message_read') as mock_mark_read:
                mock_mark_read.return_value = True
                
                response = client.post("/webhook/whatsapp", json=webhook_payload)
                
                assert response.status_code == 200
                assert response.json()["status"] == "ok"
                assert response.json()["message_id"] == "wamid.test123"
                
                # Verify that processing was called
                mock_process.assert_called_once()
                call_args = mock_process.call_args
                assert call_args[1]["phone"] == "5511888888888"
                assert call_args[1]["message_text"] == "Olá, estou com dor de cabeça"

    def test_webhook_empty_payload(self, client):
        """Test webhook with empty or invalid payload."""
        empty_payload = {
            "object": "whatsapp_business_account",
            "entry": []
        }
        
        response = client.post("/webhook/whatsapp", json=empty_payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_webhook_non_text_message(self, client):
        """Test webhook with non-text message type."""
        image_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "12345",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "12345"},
                                "messages": [
                                    {
                                        "from": "5511888888888",
                                        "id": "wamid.test123",
                                        "timestamp": "1673456789",
                                        "type": "image",
                                        "image": {"id": "image123"}
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        
        response = client.post("/webhook/whatsapp", json=image_payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        with patch('clinicai.app.db.db.client') as mock_client:
            mock_admin = AsyncMock()
            mock_admin.command = AsyncMock(return_value={"ok": 1})
            mock_client.admin = mock_admin
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "timestamp" in data
            assert data["version"] == "0.1.0"

    def test_health_endpoint_db_failure(self, client):
        """Test health endpoint when database is unavailable."""
        with patch('clinicai.app.db.db.client', None):
            response = client.get("/health")
            assert response.status_code == 503

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ClinicAI Medical Triage Agent"
        assert data["version"] == "0.1.0"
        assert "endpoints" in data


class TestWhatsAppClient:
    """Test WhatsApp client functionality."""

    @pytest.fixture
    def whatsapp_client(self):
        """Create WhatsApp client for testing."""
        return WhatsAppClient()

    def test_parse_incoming_message_valid(self, whatsapp_client):
        """Test parsing valid incoming message."""
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "msg123",
                                        "from": "5511999999999",
                                        "timestamp": "1673456789",
                                        "type": "text",
                                        "text": {"body": "Hello"}
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        
        result = whatsapp_client.parse_incoming_message(payload)
        
        assert result is not None
        assert result["message_id"] == "msg123"
        assert result["from_phone"] == "5511999999999"
        assert result["text"] == "Hello"
        assert result["timestamp"] == "1673456789"

    def test_parse_incoming_message_invalid(self, whatsapp_client):
        """Test parsing invalid message payload."""
        invalid_payloads = [
            {},  # Empty payload
            {"entry": []},  # Empty entry
            {"entry": [{"changes": []}]},  # Empty changes
            {"entry": [{"changes": [{"value": {}}]}]},  # No messages
        ]
        
        for payload in invalid_payloads:
            result = whatsapp_client.parse_incoming_message(payload)
            assert result is None

    def test_phone_number_validation(self, whatsapp_client):
        """Test phone number validation."""
        valid_phones = [
            "5511999999999",  # Brazil
            "14155552345",    # US
            "447700900123",   # UK
        ]
        
        invalid_phones = [
            "123",           # Too short
            "abc123456789",  # Contains letters
            "999888777666555444",  # Too long
        ]
        
        for phone in valid_phones:
            assert whatsapp_client.is_valid_phone_number(phone), f"Valid phone rejected: {phone}"
        
        for phone in invalid_phones:
            assert not whatsapp_client.is_valid_phone_number(phone), f"Invalid phone accepted: {phone}"

    @pytest.mark.asyncio
    async def test_send_text_message_success(self, whatsapp_client):
        """Test successful text message sending."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "msg_sent_123"}]
        }
        
        with patch.object(whatsapp_client.http_client, 'post', return_value=mock_response):
            message_id = await whatsapp_client.send_text_message(
                "5511999999999", 
                "Test message"
            )
            
            assert message_id == "msg_sent_123"

    @pytest.mark.asyncio
    async def test_send_text_message_failure(self, whatsapp_client):
        """Test message sending failure."""
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        with patch.object(whatsapp_client.http_client, 'post', return_value=mock_response):
            message_id = await whatsapp_client.send_text_message(
                "5511999999999", 
                "Test message"
            )
            
            assert message_id is None

    @pytest.mark.asyncio
    async def test_send_empty_message(self, whatsapp_client):
        """Test sending empty message."""
        message_id = await whatsapp_client.send_text_message(
            "5511999999999", 
            ""
        )
        
        assert message_id is None

    def test_webhook_signature_verification(self, whatsapp_client):
        """Test webhook signature verification (simplified)."""
        # This is a simplified test since we're not implementing full HMAC verification
        payload = "test payload"
        signature = "test signature"
        
        # Should return True in development mode
        assert whatsapp_client.verify_webhook_signature(payload, signature) is True

