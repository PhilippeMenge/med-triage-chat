"""LangGraph nodes for the triage workflow."""

import logging
from datetime import datetime
from typing import Dict, Any

from ..db import db
from ..llm import llm_client
from ..schemas import MessageDocument, TriageSlots
from ..utils.emergency import is_emergency, get_emergency_response
from ..utils.logging import log_emergency_detection, log_user_interaction
from ..utils.security import hash_phone_number, extract_phone_from_whatsapp
from ..whatsapp import whatsapp_client
from .prompts import WELCOME_MESSAGE, COMPLETION_MESSAGE, get_next_question_prompt
from .state import (
    TriageState, 
    create_initial_state, 
    update_state_from_slots, 
    is_triage_complete, 
    get_missing_slots,
    add_to_conversation_history
)

logger = logging.getLogger(__name__)


async def receive_input(state: TriageState) -> TriageState:
    """
    Node: Receive and process user input.
    
    Args:
        state: Current triage state
        
    Returns:
        Updated state with user input processed
    """
    try:
        phone = state["phone"]
        phone_hash = state["phone_hash"]
        user_text = state["last_user_text"]
        
        logger.info(f"Processing input for phone_hash: {phone_hash[:8]}...")
        
        # Load or create triage record
        existing_triage = await db.get_triage(phone_hash)
        
        if existing_triage:
            # Update state with existing triage data
            state["slots"] = existing_triage.slots.model_dump()
            state["status"] = existing_triage.status
            state["emergency_flag"] = existing_triage.emergency_flag
            state["is_first_interaction"] = False
            
            logger.info(f"Loaded existing triage for phone_hash: {phone_hash[:8]}...")
        else:
            # Create new triage
            new_triage = await db.create_triage(phone_hash)
            state["is_first_interaction"] = True
            
            logger.info(f"Created new triage for phone_hash: {phone_hash[:8]}...")
        
        # Add user message to conversation history
        state = add_to_conversation_history(state, user_text, "user")
        
        # Log interaction
        log_user_interaction(
            phone_hash=phone_hash,
            direction="in",
            message=user_text,
            metadata={"triage_status": state["status"]}
        )
        
        # Save incoming message to database
        incoming_message = MessageDocument(
            phone=phone,
            phone_hash=phone_hash,
            direction="in",
            message_id=state.get("message_id", f"in_{datetime.utcnow().timestamp()}"),
            text=user_text,
            timestamp=datetime.utcnow(),
            meta={"source": "whatsapp"},
            triage_state_snapshot=state["slots"]
        )
        
        await db.save_message(incoming_message)
        
        return state
        
    except Exception as e:
        logger.error(f"Error in receive_input: {e}")
        state["error_message"] = f"Error processing input: {e}"
        return state


async def emergency_check(state: TriageState) -> TriageState:
    """
    Node: Check for emergency keywords and handle appropriately.
    
    Args:
        state: Current triage state
        
    Returns:
        Updated state with emergency status
    """
    try:
        user_text = state["last_user_text"]
        phone_hash = state["phone_hash"]
        
        # Check for emergency using local rules
        local_emergency = is_emergency(user_text)
        
        if local_emergency:
            logger.warning(f"Emergency detected for phone_hash: {phone_hash[:8]}...")
            
            # Log emergency detection
            log_emergency_detection(
                phone_hash=phone_hash,
                message=user_text,
                detection_method="keyword_match"
            )
            
            # Update state
            state["emergency_flag"] = True
            state["status"] = "emergency"
            state["response_text"] = get_emergency_response()
            
            # Update database
            await db.update_triage(
                phone_hash=phone_hash,
                emergency_flag=True,
                status="emergency"
            )
            
            return state
        
        # No emergency detected
        state["emergency_flag"] = False
        
        logger.debug(f"No emergency detected for phone_hash: {phone_hash[:8]}...")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in emergency_check: {e}")
        state["error_message"] = f"Error checking emergency: {e}"
        return state


async def extract_slots(state: TriageState) -> TriageState:
    """
    Node: Extract structured information from user input using LLM.
    
    Args:
        state: Current triage state
        
    Returns:
        Updated state with extracted information
    """
    try:
        # Skip if emergency
        if state["emergency_flag"]:
            return state
        
        user_text = state["last_user_text"]
        conversation_history = state["conversation_history"]
        
        logger.debug("Extracting slots from user input...")
        
        # Extract slots using LLM
        extraction = await llm_client.extract_slots(
            user_text=user_text,
            conversation_history=conversation_history
        )
        
        # Check for LLM-detected emergency
        if extraction.found_emergency:
            logger.warning("LLM detected emergency in user message")
            
            log_emergency_detection(
                phone_hash=state["phone_hash"],
                message=user_text,
                detection_method="llm_detection"
            )
            
            state["emergency_flag"] = True
            state["status"] = "emergency"
            state["response_text"] = get_emergency_response()
            
            return state
        
        # Create TriageSlots object for easier handling
        current_slots = TriageSlots(**state["slots"])
        
        # Update current slots with extracted information
        extracted_slots = TriageSlots(**extraction.model_dump(exclude={"found_emergency"}))
        
        # Merge slots (keep existing non-null values)
        for field_name, field_value in extracted_slots.model_dump().items():
            if field_value is not None:
                setattr(current_slots, field_name, field_value)
        
        # Update state
        state = update_state_from_slots(state, current_slots)
        
        logger.debug(f"Slots updated. Filled: {sum(1 for v in state['slots'].values() if v is not None)}/7")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in extract_slots: {e}")
        state["error_message"] = f"Error extracting information: {e}"
        return state


async def update_state(state: TriageState) -> TriageState:
    """
    Node: Update database with current triage state.
    
    Args:
        state: Current triage state
        
    Returns:
        Updated state after database persistence
    """
    try:
        # Skip if emergency (already updated in emergency_check)
        if state["emergency_flag"]:
            return state
        
        phone_hash = state["phone_hash"]
        current_slots = TriageSlots(**state["slots"])
        
        # Determine status
        if is_triage_complete(state):
            status = "closed"
        else:
            status = "open"
        
        state["status"] = status
        
        # Update database
        await db.update_triage(
            phone_hash=phone_hash,
            slots=current_slots,
            status=status
        )
        
        logger.debug(f"Triage state updated in database. Status: {status}")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in update_state: {e}")
        state["error_message"] = f"Error updating state: {e}"
        return state


async def next_prompt(state: TriageState) -> TriageState:
    """
    Node: Generate next prompt/question for the user.
    
    Args:
        state: Current triage state
        
    Returns:
        Updated state with response text
    """
    try:
        # Skip if emergency
        if state["emergency_flag"]:
            return state
        
        # Check if triage is complete
        if is_triage_complete(state):
            state["response_text"] = COMPLETION_MESSAGE
            logger.info("Triage completed, sending completion message")
            return state
        
        # Check if this is the first interaction
        if state["is_first_interaction"]:
            state["response_text"] = WELCOME_MESSAGE
            state["is_first_interaction"] = False
            logger.info("Sending welcome message for new triage")
            return state
        
        # Generate next question using LLM
        current_slots = TriageSlots(**state["slots"])
        conversation_history = state["conversation_history"]
        
        response_text = await llm_client.generate_next_prompt(
            current_slots=current_slots,
            conversation_history=conversation_history,
            is_first_interaction=False
        )
        
        state["response_text"] = response_text
        
        logger.debug("Generated next prompt using LLM")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in next_prompt: {e}")
        
        # Fallback to rule-based prompt
        missing_slots = get_missing_slots(state)
        if missing_slots:
            fallback_prompt = get_next_question_prompt(missing_slots[0])
            state["response_text"] = fallback_prompt
        else:
            state["response_text"] = "Pode me fornecer mais informações sobre sua condição?"
        
        logger.info("Using fallback prompt due to LLM error")
        return state


async def send_whatsapp(state: TriageState) -> TriageState:
    """
    Node: Send response via WhatsApp.
    
    Args:
        state: Current triage state
        
    Returns:
        Updated state after sending message
    """
    try:
        phone = state["phone"]
        phone_hash = state["phone_hash"]
        response_text = state["response_text"]
        
        if not response_text:
            logger.warning("No response text to send")
            return state
        
        # Send message via WhatsApp
        message_id = await whatsapp_client.send_text_message(
            to_phone=phone,
            message_text=response_text
        )
        
        if message_id:
            logger.info(f"Message sent successfully: {message_id}")
            
            # Add to conversation history
            state = add_to_conversation_history(state, response_text, "assistant")
            
            # Log interaction
            log_user_interaction(
                phone_hash=phone_hash,
                direction="out",
                message=response_text,
                metadata={"message_id": message_id}
            )
            
            # Save outgoing message to database
            outgoing_message = MessageDocument(
                phone=phone,
                phone_hash=phone_hash,
                direction="out",
                message_id=message_id,
                text=response_text,
                timestamp=datetime.utcnow(),
                meta={"source": "clinicai"},
                triage_state_snapshot=state["slots"]
            )
            
            await db.save_message(outgoing_message)
            
        else:
            logger.error("Failed to send WhatsApp message")
            state["error_message"] = "Failed to send message"
        
        return state
        
    except Exception as e:
        logger.error(f"Error in send_whatsapp: {e}")
        state["error_message"] = f"Error sending message: {e}"
        return state


async def persist_message(state: TriageState) -> TriageState:
    """
    Node: Final persistence and cleanup.
    
    Args:
        state: Current triage state
        
    Returns:
        Final state
    """
    try:
        # Create or update user record
        await db.create_or_update_user(
            phone=state["phone"],
            phone_hash=state["phone_hash"]
        )
        
        logger.debug("User record updated")
        
        # Clear sensitive data from state for logging
        safe_state = state.copy()
        safe_state["phone"] = "***REDACTED***"
        
        logger.info(f"Triage workflow completed. Status: {state['status']}")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in persist_message: {e}")
        state["error_message"] = f"Error persisting data: {e}"
        return state


# Node mapping for the workflow
WORKFLOW_NODES = {
    "receive_input": receive_input,
    "emergency_check": emergency_check,
    "extract_slots": extract_slots,
    "update_state": update_state,
    "next_prompt": next_prompt,
    "send_whatsapp": send_whatsapp,
    "persist_message": persist_message,
}

