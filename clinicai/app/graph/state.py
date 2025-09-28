"""LangGraph state management for triage workflow."""

from typing import Dict, List, Literal, Optional, TypedDict

from ..schemas import TriageSlots


class TriageState(TypedDict):
    """State object for the triage workflow."""
    
    # User identification
    phone: str
    phone_hash: str
    
    # Current interaction
    last_user_text: str
    conversation_history: List[str]
    
    # Triage data
    slots: Dict[str, Optional[str]]
    emergency_flag: bool
    status: Literal["open", "closed", "emergency"]
    
    # Workflow control
    is_first_interaction: bool
    response_text: str
    message_id: Optional[str]
    
    # Error handling
    error_message: Optional[str]
    retry_count: int


def create_initial_state(phone: str, phone_hash: str, user_text: str) -> TriageState:
    """
    Create initial state for a new triage session.
    
    Args:
        phone: User's phone number
        phone_hash: Hashed phone number
        user_text: Initial user message
        
    Returns:
        Initial triage state
    """
    return TriageState(
        phone=phone,
        phone_hash=phone_hash,
        last_user_text=user_text,
        conversation_history=[],
        slots={
            "chief_complaint": None,
            "symptoms": None,
            "duration": None,
            "frequency": None,
            "intensity": None,
            "history": None,
            "measures_taken": None,
        },
        emergency_flag=False,
        status="open",
        is_first_interaction=True,
        response_text="",
        message_id=None,
        error_message=None,
        retry_count=0,
    )


def update_state_from_slots(state: TriageState, slots: TriageSlots) -> TriageState:
    """
    Update state with extracted slot information.
    
    Args:
        state: Current state
        slots: Extracted slots
        
    Returns:
        Updated state
    """
    # Update only non-null slots
    slot_dict = slots.model_dump()
    for key, value in slot_dict.items():
        if value is not None:
            state["slots"][key] = value
    
    return state


def is_triage_complete(state: TriageState) -> bool:
    """
    Check if triage is complete (all slots filled).
    
    Args:
        state: Current state
        
    Returns:
        True if all slots are filled
    """
    return all(value is not None for value in state["slots"].values())


def get_missing_slots(state: TriageState) -> List[str]:
    """
    Get list of missing slot names.
    
    Args:
        state: Current state
        
    Returns:
        List of missing slot names
    """
    return [key for key, value in state["slots"].items() if value is None]


def add_to_conversation_history(state: TriageState, message: str, role: str = "user") -> TriageState:
    """
    Add message to conversation history.
    
    Args:
        state: Current state
        message: Message to add
        role: Message role (user or assistant)
        
    Returns:
        Updated state
    """
    formatted_message = f"{role}: {message}"
    state["conversation_history"].append(formatted_message)
    
    # Keep only last 10 messages for performance
    if len(state["conversation_history"]) > 10:
        state["conversation_history"] = state["conversation_history"][-10:]
    
    return state

