"""FastAPI application for ClinicAI medical triage agent."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from .config import settings
from .db import db
from .graph.workflow import process_whatsapp_message, get_triage_status
from .schemas import (
    HealthResponse,
    IncomingWhatsAppPayload,
    TriageResponse,
    WebhookResponse,
)
from .utils.logging import setup_logging, log_whatsapp_error
from .utils.security import sanitize_log_data
from .whatsapp import whatsapp_client, verify_webhook_token

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting ClinicAI application...")
    
    try:
        # Connect to database
        await db.connect()
        logger.info("Database connected successfully")
        
        # Verify LLM configuration
        from .llm import llm_client
        logger.info("LLM client initialized")
        
        # Verify WhatsApp configuration
        logger.info("WhatsApp client initialized")
        
        logger.info("ClinicAI application started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down ClinicAI application...")
    
    try:
        # Close database connection
        await db.disconnect()
        
        # Close WhatsApp client
        await whatsapp_client.close()
        
        logger.info("Application shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="ClinicAI Medical Triage Agent",
    description="AI-powered medical triage agent for WhatsApp integration",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware (disabled by default for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # Empty list = no CORS
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP exception handler."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# Health check endpoint
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check",
    description="Check if the application is running and healthy"
)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    try:
        # Test database connection
        if db.client:
            await db.client.admin.command("ping")
        
        return HealthResponse(
            status="ok",
            timestamp=datetime.utcnow(),
            version="0.1.0"
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable - database connection failed"
        )


# WhatsApp webhook verification (GET)
@app.get(
    "/webhook/whatsapp",
    tags=["webhook"],
    summary="WhatsApp webhook verification",
    description="Verify WhatsApp webhook during setup"
)
async def verify_whatsapp_webhook(
    request: Request,
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
) -> PlainTextResponse:
    """
    Verify WhatsApp webhook during Meta configuration.
    
    Args:
        hub_mode: Verification mode from Meta
        hub_verify_token: Verification token from Meta
        hub_challenge: Challenge string to return
        
    Returns:
        Challenge string if verification succeeds
    """
    logger.info(f"Webhook verification request: mode={hub_mode}")
    
    # Validate mode
    if hub_mode != "subscribe":
        logger.warning(f"Invalid webhook mode: {hub_mode}")
        raise HTTPException(status_code=400, detail="Invalid mode")
    
    # Verify token
    if not verify_webhook_token(hub_verify_token):
        logger.warning("Invalid webhook verification token")
        raise HTTPException(status_code=403, detail="Forbidden")
    
    logger.info("Webhook verification successful")
    return PlainTextResponse(content=hub_challenge)


# WhatsApp webhook message handler (POST)
@app.post(
    "/webhook/whatsapp",
    response_model=WebhookResponse,
    tags=["webhook"],
    summary="WhatsApp message webhook",
    description="Handle incoming WhatsApp messages"
)
async def handle_whatsapp_webhook(
    request: Request,
    payload: IncomingWhatsAppPayload
) -> WebhookResponse:
    """
    Handle incoming WhatsApp messages.
    
    Args:
        payload: WhatsApp webhook payload
        
    Returns:
        Processing status response
    """
    try:
        logger.info("Received WhatsApp webhook")
        
        # Parse the incoming message
        parsed_message = whatsapp_client.parse_incoming_message(
            payload.model_dump()
        )
        
        if not parsed_message:
            logger.info("No valid message in webhook payload")
            return WebhookResponse(status="ok")
        
        # Extract message details
        phone = parsed_message["from_phone"]
        message_text = parsed_message["text"]
        message_id = parsed_message["message_id"]
        
        logger.info(f"Processing message: {sanitize_log_data(message_text[:50])}...")
        
        # Validate phone number
        if not whatsapp_client.is_valid_phone_number(phone):
            logger.warning(f"Invalid phone number format: {sanitize_log_data(phone)}")
            return WebhookResponse(status="ok")
        
        # Process through triage workflow
        result = await process_whatsapp_message(
            phone=phone,
            message_text=message_text,
            message_id=message_id
        )
        
        if result["success"]:
            logger.info(f"Message processed successfully: {result['status']}")
            
            # Mark message as read
            if message_id:
                await whatsapp_client.mark_message_read(message_id)
                
        else:
            logger.error(f"Message processing failed: {result.get('error')}")
            
            log_whatsapp_error(
                error_type="processing_failed",
                error_message=result.get("error", "Unknown error"),
                phone_number=phone
            )
        
        return WebhookResponse(
            status="ok",
            message_id=message_id
        )
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        
        log_whatsapp_error(
            error_type="webhook_error",
            error_message=str(e)
        )
        
        # Return 200 to prevent WhatsApp retries
        return WebhookResponse(status="error")


# Get triage status endpoint
@app.get(
    "/triages/{phone_hash}",
    response_model=TriageResponse,
    tags=["triage"],
    summary="Get triage status",
    description="Get current triage information for a phone number hash"
)
async def get_triage_info(phone_hash: str) -> TriageResponse:
    """
    Get triage information by phone hash.
    
    Args:
        phone_hash: Hashed phone number
        
    Returns:
        Triage information
    """
    try:
        logger.info(f"Fetching triage for phone_hash: {phone_hash[:8]}...")
        
        # Validate phone hash format
        if len(phone_hash) != 64:  # SHA-256 hash length
            raise HTTPException(
                status_code=400,
                detail="Invalid phone hash format"
            )
        
        # Get triage from database
        triage = await db.get_triage(phone_hash)
        
        if not triage:
            raise HTTPException(
                status_code=404,
                detail="Triage not found"
            )
        
        return TriageResponse(
            phone_hash=phone_hash,
            status=triage.status,
            slots=triage.slots,
            emergency_flag=triage.emergency_flag,
            created_at=triage.created_at,
            updated_at=triage.updated_at,
            last_message_at=triage.last_message_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching triage: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


# Additional endpoints for monitoring/admin (optional)
@app.get(
    "/triages",
    tags=["triage"],
    summary="List recent triages",
    description="List recent triages for monitoring (admin endpoint)"
)
async def list_recent_triages(
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None)
) -> Dict[str, Any]:
    """
    List recent triages for monitoring.
    
    Args:
        limit: Maximum number of triages to return
        status: Filter by status (open, closed, emergency)
        
    Returns:
        List of recent triages
    """
    try:
        # Simple implementation - in production, add proper authentication
        logger.info(f"Listing recent triages: limit={limit}, status={status}")
        
        # This is a simplified version - implement proper pagination and filtering
        if not db.db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Build query
        query = {}
        if status:
            query["status"] = status
        
        # Fetch triages
        cursor = (
            db.db.triages.find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        
        triages = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            # Remove sensitive data for listing
            triage_summary = {
                "phone_hash": doc["phone_hash"][:8] + "...",
                "status": doc["status"],
                "emergency_flag": doc["emergency_flag"],
                "created_at": doc["created_at"].isoformat(),
                "updated_at": doc["updated_at"].isoformat(),
                "slots_filled": sum(1 for v in doc["slots"].values() if v is not None),
            }
            triages.append(triage_summary)
        
        return {
            "triages": triages,
            "count": len(triages),
            "filters": {"status": status, "limit": limit},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing triages: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


# Root endpoint
@app.get(
    "/",
    tags=["health"],
    summary="Root endpoint",
    description="Basic application information"
)
async def root() -> Dict[str, Any]:
    """Root endpoint with basic information."""
    return {
        "name": "ClinicAI Medical Triage Agent",
        "version": "0.1.0",
        "description": "AI-powered medical triage agent for WhatsApp",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "webhook": "/webhook/whatsapp",
            "triages": "/triages/{phone_hash}",
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=True,
    )

