"""LangGraph workflow definition for the triage agent."""

import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from .state import TriageState, create_initial_state
from .nodes import (
    receive_input,
    emergency_check,
    extract_slots,
    update_state,
    next_prompt,
    send_whatsapp,
    persist_message,
)
from ..utils.security import hash_phone_number, extract_phone_from_whatsapp

logger = logging.getLogger(__name__)


def should_end_workflow(state: TriageState) -> str:
    """
    Determine if workflow should end based on state.
    
    Args:
        state: Current triage state
        
    Returns:
        Next node name or END
    """
    # End if emergency detected
    if state["emergency_flag"]:
        return "send_whatsapp"
    
    # End if error occurred
    if state.get("error_message"):
        logger.error(f"Workflow error: {state['error_message']}")
        return END
    
    # Continue to slot extraction
    return "extract_slots"


def should_continue_triage(state: TriageState) -> str:
    """
    Determine if triage should continue after slot extraction.
    
    Args:
        state: Current triage state
        
    Returns:
        Next node name
    """
    # Emergency detected during extraction
    if state["emergency_flag"]:
        return "update_state"
    
    # Error occurred
    if state.get("error_message"):
        return END
    
    # Continue normal flow
    return "update_state"


# Create the workflow graph
def create_triage_workflow() -> StateGraph:
    """
    Create the LangGraph workflow for triage processing.
    
    Returns:
        Configured StateGraph for triage workflow
    """
    # Initialize the graph
    workflow = StateGraph(TriageState)
    
    # Add nodes
    workflow.add_node("receive_input", receive_input)
    workflow.add_node("emergency_check", emergency_check)
    workflow.add_node("extract_slots", extract_slots)
    workflow.add_node("update_state", update_state)
    workflow.add_node("next_prompt", next_prompt)
    workflow.add_node("send_whatsapp", send_whatsapp)
    workflow.add_node("persist_message", persist_message)
    
    # Set entry point
    workflow.set_entry_point("receive_input")
    
    # Add edges with conditional logic
    workflow.add_edge("receive_input", "emergency_check")
    
    # Conditional edge from emergency_check
    workflow.add_conditional_edges(
        "emergency_check",
        should_end_workflow,
        {
            "extract_slots": "extract_slots",
            "send_whatsapp": "send_whatsapp",
        }
    )
    
    # Conditional edge from extract_slots
    workflow.add_conditional_edges(
        "extract_slots",
        should_continue_triage,
        {
            "update_state": "update_state",
        }
    )
    
    # Linear flow after state update
    workflow.add_edge("update_state", "next_prompt")
    workflow.add_edge("next_prompt", "send_whatsapp")
    workflow.add_edge("send_whatsapp", "persist_message")
    workflow.add_edge("persist_message", END)
    
    return workflow


# Create the compiled workflow
triage_workflow = create_triage_workflow().compile()


async def process_whatsapp_message(
    phone: str, 
    message_text: str, 
    message_id: str = None
) -> Dict[str, Any]:
    """
    Process an incoming WhatsApp message through the triage workflow.
    
    Args:
        phone: User's phone number
        message_text: Text content of the message
        message_id: WhatsApp message ID
        
    Returns:
        Processing result with status and response
    """
    try:
        # Normalize and hash phone number
        normalized_phone = extract_phone_from_whatsapp(phone)
        phone_hash = hash_phone_number(normalized_phone)
        
        logger.info(f"Processing message for phone_hash: {phone_hash[:8]}...")
        
        # Create initial state
        initial_state = create_initial_state(
            phone=normalized_phone,
            phone_hash=phone_hash,
            user_text=message_text
        )
        
        if message_id:
            initial_state["message_id"] = message_id
        
        # Run the workflow
        final_state = await triage_workflow.ainvoke(initial_state)
        
        # Extract result
        result = {
            "success": not bool(final_state.get("error_message")),
            "status": final_state["status"],
            "emergency": final_state["emergency_flag"],
            "response_sent": bool(final_state.get("response_text")),
            "phone_hash": phone_hash,
        }
        
        if final_state.get("error_message"):
            result["error"] = final_state["error_message"]
        
        logger.info(f"Workflow completed. Result: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in workflow processing: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": "error",
            "emergency": False,
            "response_sent": False,
        }


async def get_triage_status(phone: str) -> Dict[str, Any]:
    """
    Get current triage status for a phone number.
    
    Args:
        phone: User's phone number
        
    Returns:
        Current triage status information
    """
    try:
        # Normalize and hash phone
        normalized_phone = extract_phone_from_whatsapp(phone)
        phone_hash = hash_phone_number(normalized_phone)
        
        # Import here to avoid circular imports
        from ..db import db
        
        # Get triage from database
        triage = await db.get_triage(phone_hash)
        
        if not triage:
            return {
                "exists": False,
                "phone_hash": phone_hash,
            }
        
        # Count filled slots
        filled_slots = sum(1 for v in triage.slots.model_dump().values() if v is not None)
        total_slots = len(triage.slots.model_fields)
        
        return {
            "exists": True,
            "phone_hash": phone_hash,
            "status": triage.status,
            "emergency_flag": triage.emergency_flag,
            "slots_filled": filled_slots,
            "total_slots": total_slots,
            "completion_rate": round(filled_slots / total_slots * 100, 1),
            "created_at": triage.created_at.isoformat(),
            "updated_at": triage.updated_at.isoformat(),
            "last_message_at": triage.last_message_at.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error getting triage status: {e}")
        return {
            "exists": False,
            "error": str(e),
        }

