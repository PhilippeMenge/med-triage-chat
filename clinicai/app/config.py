"""Configuration settings for ClinicAI application."""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server Configuration
    port: int = Field(default=8000, description="Server port")
    base_url: str = Field(default="http://localhost:8000", description="Base URL")

    # Database
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017", description="MongoDB connection URI"
    )
    mongodb_db: str = Field(default="clinicai", description="MongoDB database name")

    # Security
    phone_hash_salt: str = Field(
        default="change-me", description="Salt for phone number hashing"
    )

    # LLM Integration
    gemini_api_key: str = Field(description="Google Gemini API key")

    # WhatsApp Cloud API
    whatsapp_access_token: str = Field(description="WhatsApp Cloud API access token")
    whatsapp_phone_number_id: str = Field(description="WhatsApp phone number ID")
    whatsapp_verify_token: str = Field(description="WhatsApp webhook verify token")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @property
    def webhook_url(self) -> str:
        """Get the webhook URL for WhatsApp verification."""
        return f"{self.base_url}/webhook/whatsapp"


# Global settings instance
settings = Settings()

