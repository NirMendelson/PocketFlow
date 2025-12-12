"""Utility functions for fetching workflow context from shared store."""

from typing import Dict, Any, List


def get_workflow_context(shared: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch workflow execution context from shared store.
    
    Args:
        shared: The shared store dictionary
        
    Returns:
        Dictionary containing:
            - selected_workflow: The currently selected workflow
            - current_step: Current step information
            - conversation_history: List of conversation messages
            - constants: Workflow constants
            - tone_config: Tone configuration
            - extracted_fields: Fields extracted during workflow execution
    """
    selected_workflow = shared.get("selected_workflow")
    current_step = shared.get("current_step", {})
    conversation_history = shared.get("conversation_history", [])
    constants = shared.get("constants", {})
    tone_config = shared.get("tone_config", {})
    extracted_fields = shared.get("extracted_fields", {})
    
    return {
        "selected_workflow": selected_workflow,
        "current_step": current_step,
        "conversation_history": conversation_history,
        "constants": constants,
        "tone_config": tone_config,
        "extracted_fields": extracted_fields
    }

