"""Workflow step execution utilities."""

from typing import Dict, List, Any, Optional
from utils.action_executor import (
    execute_fetch,
    evaluate_condition,
    execute_reply,
    execute_tool,
    execute_include
)
from utils.workflow_registry import build_step_registry, get_next_step_id, get_first_step_id


def validate_workflow_execution(selected_workflow: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate that workflow exists and has steps.
    
    Args:
        selected_workflow: The selected workflow dictionary
        
    Returns:
        Dictionary with validation result:
            - valid: bool indicating if workflow is valid
            - status: "no_workflow" or "complete" if invalid
            - workflow_def: workflow definition if valid
            - steps: list of steps if valid
    """
    if not selected_workflow:
        return {
            "valid": False,
            "status": "no_workflow",
            "workflow_def": None,
            "steps": None
        }
    
    workflow_def = selected_workflow.get("definition", {})
    steps = workflow_def.get("steps", [])
    
    if not steps:
        return {
            "valid": False,
            "status": "complete",
            "workflow_def": workflow_def,
            "steps": steps
        }
    
    return {
        "valid": True,
        "status": None,
        "workflow_def": workflow_def,
        "steps": steps
    }


def get_current_step_with_fallback(
    current_step_id: Optional[str],
    steps: List[Dict[str, Any]],
    step_registry: Dict[str, Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Get current step, or initialize to first step if none exists.
    
    Args:
        current_step_id: Current step ID from context
        steps: List of workflow steps
        step_registry: Registry mapping step IDs to step definitions
        
    Returns:
        Step definition dictionary, or None if no step found
    """
    # If no current step, start with first step
    if not current_step_id:
        current_step_id = get_first_step_id(steps)
        if not current_step_id:
            return None
    
    # Get step from registry
    step = step_registry.get(current_step_id)
    return step


def check_and_handle_prerequisites(
    current_step_id: str,
    steps: List[Dict[str, Any]],
    constants: Dict[str, Any],
    conversation_history: List[Dict[str, str]]
) -> None:
    """
    Check and handle prerequisites if this is the first step.
    
    Args:
        current_step_id: Current step ID
        steps: List of workflow steps
        constants: Workflow constants
        conversation_history: Conversation history
    """
    if current_step_id != get_first_step_id(steps):
        return
    
    default_prereqs = constants.get("default_prerequisites", [])
    for prereq_field in default_prereqs:
        # Try to extract prerequisite fields from conversation
        # This is a simplified version - in practice, you might want to use LLM
        # For now, we'll assume state is always extracted from user input
        if prereq_field == "state":
            # Extract state from conversation (e.g., "I'm from NY")
            for msg in conversation_history:
                content = msg.get("content", "").lower()
                # Simple extraction - look for "from [state]" pattern
                if "from" in content:
                    # This is a placeholder - real implementation would use LLM
                    pass


def build_step_result(
    status: str,
    next_step_id: Optional[str],
    extracted_fields: Optional[Dict[str, str]] = None,
    reply: Optional[str] = None,
    include_info: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build standardized step execution result.
    
    Args:
        status: Execution status ("continue", "complete", "no_workflow")
        next_step_id: ID of next step to execute
        extracted_fields: Updated extracted fields (optional)
        reply: Generated reply message (optional)
        include_info: Include information (optional)
        
    Returns:
        Standardized result dictionary
    """
    result = {
        "status": status,
        "next_step_id": next_step_id
    }
    
    if extracted_fields is not None:
        result["extracted_fields"] = extracted_fields
    
    if reply is not None:
        result["reply"] = reply
    
    if include_info is not None:
        result["include_info"] = include_info
    
    return result


def determine_workflow_status(next_step_id: Optional[str]) -> str:
    """
    Determine workflow status based on next step availability.
    
    Args:
        next_step_id: ID of next step, or None if complete
        
    Returns:
        "continue" if next step exists, "complete" otherwise
    """
    return "continue" if next_step_id else "complete"


def handle_fetch_action(
    step: Dict[str, Any],
    current_step_id: str,
    steps: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]],
    extracted_fields: Dict[str, str]
) -> Dict[str, Any]:
    """
    Handle fetch action execution.
    
    Args:
        step: Step definition
        current_step_id: Current step ID
        steps: List of workflow steps
        conversation_history: Conversation history
        extracted_fields: Current extracted fields
        
    Returns:
        Step execution result
    """
    result = execute_fetch(step, conversation_history)
    
    if result.get("found"):
        extracted_fields[result["field_name"]] = result["value"]
    
    next_step_id = get_next_step_id(current_step_id, steps)
    status = determine_workflow_status(next_step_id)
    
    return build_step_result(
        status=status,
        next_step_id=next_step_id,
        extracted_fields=extracted_fields
    )


def handle_conditional_action(
    step: Dict[str, Any],
    current_step_id: str,
    steps: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]],
    extracted_fields: Dict[str, str]
) -> Dict[str, Any]:
    """
    Handle conditional action execution.
    
    Args:
        step: Step definition
        current_step_id: Current step ID
        steps: List of workflow steps
        conversation_history: Conversation history
        extracted_fields: Current extracted fields
        
    Returns:
        Step execution result
    """
    condition = step.get("condition", {})
    condition_result = evaluate_condition(condition, conversation_history, extracted_fields)
    
    next_step_id = get_next_step_id(current_step_id, steps, condition_result)
    status = determine_workflow_status(next_step_id)
    
    return build_step_result(
        status=status,
        next_step_id=next_step_id
    )


def handle_reply_action(
    step: Dict[str, Any],
    current_step_id: str,
    steps: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]],
    tone_config: Dict[str, Any],
    extracted_fields: Dict[str, str]
) -> Dict[str, Any]:
    """
    Handle reply action execution.
    
    Args:
        step: Step definition
        current_step_id: Current step ID
        steps: List of workflow steps
        conversation_history: Conversation history
        tone_config: Tone configuration
        extracted_fields: Current extracted fields
        
    Returns:
        Step execution result
    """
    reply = execute_reply(step, conversation_history, tone_config, extracted_fields)
    next_step_id = get_next_step_id(current_step_id, steps)
    status = determine_workflow_status(next_step_id)
    
    return build_step_result(
        status=status,
        next_step_id=next_step_id,
        reply=reply
    )


def handle_tool_action(
    step: Dict[str, Any],
    current_step_id: str,
    steps: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]],
    tone_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handle tool action execution.
    
    Args:
        step: Step definition
        current_step_id: Current step ID
        steps: List of workflow steps
        conversation_history: Conversation history
        tone_config: Tone configuration
        
    Returns:
        Step execution result
    """
    execute_tool(step, conversation_history, tone_config)
    next_step_id = get_next_step_id(current_step_id, steps)
    status = determine_workflow_status(next_step_id)
    
    return build_step_result(
        status=status,
        next_step_id=next_step_id
    )


def handle_include_action(
    step: Dict[str, Any],
    current_step_id: str,
    steps: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Handle include action execution.
    
    Args:
        step: Step definition
        current_step_id: Current step ID
        steps: List of workflow steps
        
    Returns:
        Step execution result
    """
    info = execute_include(step)
    next_step_id = get_next_step_id(current_step_id, steps)
    status = determine_workflow_status(next_step_id)
    
    return build_step_result(
        status=status,
        next_step_id=next_step_id,
        include_info=info
    )


def execute_workflow_step(prep_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single workflow step based on context.
    
    This is the main orchestrator function that:
    1. Validates workflow execution context
    2. Gets current step
    3. Handles prerequisites
    4. Routes to appropriate action handler
    
    Args:
        prep_res: Prepared context from prep() containing:
            - selected_workflow: Selected workflow
            - current_step: Current step info
            - conversation_history: Conversation history
            - constants: Workflow constants
            - tone_config: Tone configuration
            - extracted_fields: Extracted fields
            
    Returns:
        Step execution result dictionary
    """
    # Extract context
    selected_workflow = prep_res["selected_workflow"]
    current_step_id = prep_res["current_step"].get("step_id") if prep_res["current_step"] else None
    conversation_history = prep_res["conversation_history"]
    constants = prep_res["constants"]
    tone_config = prep_res["tone_config"]
    extracted_fields = prep_res["extracted_fields"]
    
    # Validate workflow
    validation = validate_workflow_execution(selected_workflow)
    if not validation["valid"]:
        return build_step_result(
            status=validation["status"],
            next_step_id=None
        )
    
    steps = validation["steps"]
    
    # Build step registry
    step_registry = build_step_registry(steps)
    
    # Get current step
    step = get_current_step_with_fallback(current_step_id, steps, step_registry)
    if not step:
        return build_step_result(
            status="complete",
            next_step_id=None
        )
    
    # Update current_step_id if it was None (initialized to first step)
    if not current_step_id:
        current_step_id = step.get("id")
    
    # Check prerequisites if this is the first step
    check_and_handle_prerequisites(current_step_id, steps, constants, conversation_history)
    
    # Route to appropriate action handler
    action = step.get("action", "")
    
    if action == "fetch":
        return handle_fetch_action(
            step, current_step_id, steps, conversation_history, extracted_fields
        )
    elif action == "conditional":
        return handle_conditional_action(
            step, current_step_id, steps, conversation_history, extracted_fields
        )
    elif action == "reply":
        return handle_reply_action(
            step, current_step_id, steps, conversation_history, tone_config, extracted_fields
        )
    elif action == "use_tool":
        return handle_tool_action(
            step, current_step_id, steps, conversation_history, tone_config
        )
    elif action == "include":
        return handle_include_action(step, current_step_id, steps)
    else:
        raise ValueError(f"unknown action type: '{action}' in step '{current_step_id}'")

