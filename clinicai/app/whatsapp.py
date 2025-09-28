"""WhatsApp Cloud API integration for sending and receiving messages."""

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from .config import settings
from .schemas import OutgoingWhatsAppMessage, OutgoingWhatsAppText
from .utils.logging import log_whatsapp_error
from .utils.security import sanitize_log_data

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """WhatsApp Cloud API client for messaging operations."""

    def __init__(self) -> None:
        """Initialize WhatsApp client."""
        self.base_url = "https://graph.facebook.com/v20.0"
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.access_token = settings.whatsapp_access_token
        
        # HTTP client configuration
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()

    async def send_text_message(
        self, 
        to_phone: str, 
        message_text: str,
        retry_count: int = 3
    ) -> Optional[str]:
        """
        Send a text message via WhatsApp Cloud API.
        
        Args:
            to_phone: Recipient phone number
            message_text: Text message to send
            retry_count: Number of retry attempts for failed requests
            
        Returns:
            Message ID if successful, None if failed
        """
        if not message_text.strip():
            logger.warning("Attempted to send empty message")
            return None

        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        # Create message payload
        message = OutgoingWhatsAppMessage(
            to=to_phone,
            text=OutgoingWhatsAppText(body=message_text)
        )

        # Attempt to send with retries
        for attempt in range(retry_count):
            try:
                logger.info(f"Sending WhatsApp message (attempt {attempt + 1}/{retry_count})")
                
                response = await self.http_client.post(
                    url,
                    headers=headers,
                    json=message.model_dump(),
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    message_id = response_data.get("messages", [{}])[0].get("id")
                    
                    logger.info(f"Message sent successfully: {message_id}")
                    return message_id
                
                elif response.status_code == 429:
                    # Rate limit - wait and retry
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                    continue
                
                else:
                    # Log error and retry for 5xx errors
                    error_text = response.text
                    logger.error(f"WhatsApp API error: {response.status_code} - {sanitize_log_data(error_text)}")
                    
                    log_whatsapp_error(
                        error_type="send_failed",
                        error_message=error_text,
                        phone_number=to_phone,
                        response_status=response.status_code,
                    )
                    
                    if 500 <= response.status_code < 600 and attempt < retry_count - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Server error. Retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        break

            except httpx.TimeoutException:
                logger.error(f"Timeout sending message (attempt {attempt + 1})")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    log_whatsapp_error(
                        error_type="timeout",
                        error_message="Request timeout",
                        phone_number=to_phone,
                    )
                    break

            except Exception as e:
                logger.error(f"Unexpected error sending message: {e}")
                log_whatsapp_error(
                    error_type="unexpected_error",
                    error_message=str(e),
                    phone_number=to_phone,
                )
                break

        logger.error(f"Failed to send message after {retry_count} attempts")
        return None

    async def mark_message_read(self, message_id: str) -> bool:
        """
        Mark a message as read.
        
        Args:
            message_id: WhatsApp message ID to mark as read
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        try:
            response = await self.http_client.post(
                url, 
                headers=headers, 
                json=payload
            )
            
            if response.status_code == 200:
                logger.debug(f"Message marked as read: {message_id}")
                return True
            else:
                logger.warning(f"Failed to mark message as read: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return False

    def verify_webhook_signature(
        self, 
        payload: str, 
        signature: str
    ) -> bool:
        """
        Verify webhook signature (simplified - in production use proper HMAC).
        
        Args:
            payload: Raw request payload
            signature: X-Hub-Signature-256 header
            
        Returns:
            True if signature is valid
        """
        # For production, implement proper HMAC verification
        # For now, we'll skip signature verification
        logger.debug("Webhook signature verification skipped (development mode)")
        return True

    def parse_incoming_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse incoming WhatsApp webhook payload to extract message information.
        
        Args:
            payload: Raw webhook payload
            
        Returns:
            Parsed message data or None if not a valid message
        """
        try:
            entry = payload.get("entry", [])
            if not entry:
                return None

            changes = entry[0].get("changes", [])
            if not changes:
                return None

            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                logger.debug("No messages in webhook payload")
                return None

            message = messages[0]
            
            # Only process text messages for now
            if message.get("type") != "text":
                logger.debug(f"Ignoring non-text message type: {message.get('type')}")
                return None

            return {
                "message_id": message.get("id"),
                "from_phone": message.get("from"),
                "timestamp": message.get("timestamp"),
                "text": message.get("text", {}).get("body", ""),
                "raw_payload": payload,
            }

        except Exception as e:
            logger.error(f"Error parsing incoming message: {e}")
            log_whatsapp_error(
                error_type="parse_error",
                error_message=str(e),
            )
            return None

    def is_valid_phone_number(self, phone: str) -> bool:
        """
        Validate phone number format.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            True if valid format
        """
        import re
        
        # Remove all non-digit characters
        digits_only = re.sub(r"\D", "", phone)
        
        # Should be between 10-15 digits (international format)
        if not 10 <= len(digits_only) <= 15:
            return False
        
        # Should start with country code
        if not digits_only.startswith(("55", "1", "44", "49", "33")):  # Common country codes
            return False
        
        return True


# Global WhatsApp client instance
whatsapp_client = WhatsAppClient()


# Convenience functions for backward compatibility
async def send_text(
    phone_number_id: str,
    access_token: str, 
    to_phone: str, 
    message_text: str
) -> Optional[str]:
    """
    Legacy function for sending text messages.
    
    Args:
        phone_number_id: WhatsApp phone number ID (ignored, uses config)
        access_token: Access token (ignored, uses config)
        to_phone: Recipient phone number
        message_text: Message text
        
    Returns:
        Message ID if successful
    """
    return await whatsapp_client.send_text_message(to_phone, message_text)


async def verify_webhook_token(hub_verify_token: str) -> bool:
    """
    Verify webhook verification token.
    
    Args:
        hub_verify_token: Token from webhook verification request
        
    Returns:
        True if token matches configuration
    """
    expected_token = settings.whatsapp_verify_token
    is_valid = hub_verify_token == expected_token
    
    if not is_valid:
        logger.warning("Invalid webhook verification token received")
    
    return is_valid

