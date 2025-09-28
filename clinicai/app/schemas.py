"""Pydantic schemas for data validation and serialization."""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


# WhatsApp Integration Schemas
class WhatsAppTextMessage(BaseModel):
    """WhatsApp text message structure."""

    body: str


class WhatsAppMessage(BaseModel):
    """Individual WhatsApp message."""

    from_: str = Field(alias="from")
    id: str
    timestamp: str
    text: WhatsAppTextMessage
    type: str = "text"


class WhatsAppValue(BaseModel):
    """WhatsApp webhook value structure."""

    messaging_product: str
    metadata: Dict[str, Any]
    contacts: Optional[list] = None
    messages: list[WhatsAppMessage]


class WhatsAppEntry(BaseModel):
    """WhatsApp webhook entry structure."""

    id: str
    changes: list[Dict[str, Any]]


class IncomingWhatsAppPayload(BaseModel):
    """Incoming WhatsApp webhook payload."""

    object: str
    entry: list[WhatsAppEntry]


# Outgoing WhatsApp Message
class OutgoingWhatsAppText(BaseModel):
    """Outgoing WhatsApp text content."""

    preview_url: bool = False
    body: str


class OutgoingWhatsAppMessage(BaseModel):
    """Outgoing WhatsApp message structure."""

    messaging_product: str = "whatsapp"
    to: str
    type: str = "text"
    text: OutgoingWhatsAppText


# Triage Data Schemas
class TriageSlots(BaseModel):
    """Structured triage information slots."""

    chief_complaint: Optional[str] = None
    symptoms: Optional[str] = None
    duration: Optional[str] = None
    frequency: Optional[str] = None
    intensity: Optional[str] = None
    history: Optional[str] = None
    measures_taken: Optional[str] = None

    def is_complete(self) -> bool:
        """Check if all slots are filled."""
        return all(
            getattr(self, field) is not None
            for field in self.model_fields.keys()
        )

    def get_missing_slots(self) -> list[str]:
        """Get list of missing slots."""
        return [
            field
            for field in self.model_fields.keys()
            if getattr(self, field) is None
        ]


class TriageDocument(BaseModel):
    """MongoDB triage document structure."""

    phone_hash: str
    status: Literal["open", "closed", "emergency"]
    slots: TriageSlots
    emergency_flag: bool = False
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    last_message_at: datetime

    class Config:
        arbitrary_types_allowed = True


class MessageDocument(BaseModel):
    """MongoDB message document structure."""

    phone: str
    phone_hash: str
    direction: Literal["in", "out"]
    message_id: str
    text: str
    timestamp: datetime
    meta: Dict[str, Any]
    triage_state_snapshot: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True


class UserDocument(BaseModel):
    """MongoDB user document structure (optional)."""

    phone: str
    phone_hash: str
    created_at: datetime
    last_seen_at: datetime

    class Config:
        arbitrary_types_allowed = True


# LLM Extraction Schema
class LLMExtraction(BaseModel):
    """LLM slot extraction result."""

    chief_complaint: Optional[str] = None
    symptoms: Optional[str] = None
    duration: Optional[str] = None
    frequency: Optional[str] = None
    intensity: Optional[str] = None
    history: Optional[str] = None
    measures_taken: Optional[str] = None
    found_emergency: bool = False


# API Response Schemas
class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    timestamp: datetime
    version: str = "0.1.0"


class WebhookResponse(BaseModel):
    """Webhook processing response."""

    status: str = "ok"
    message_id: Optional[str] = None


class TriageResponse(BaseModel):
    """Triage information response."""

    phone_hash: str
    status: Literal["open", "closed", "emergency"]
    slots: TriageSlots
    emergency_flag: bool
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime

