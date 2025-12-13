import os
from typing import Dict, List, Any, Optional
from utils.action_executor import (
    execute_fetch,
    evaluate_condition,
    execute_reply,
    execute_tool,
    execute_include
)
from utils.workflow_registry import build_step_registry, get_next_step_id, get_first_step_id


def _is_debugging_enabled():
    """Check if DEBUGGING_MODE is enabled from environment variables."""
    return os.environ.get("DEBUGGING_MODE", "").lower() in ("true", "1", "yes")


def _log_workflow_step(workflow_name: str, step_id: str, action: str, outcome: str):
    """Log workflow step execution details when debugging is enabled."""
    if not _is_debugging_enabled():
        return
    print(f"[DEBUG] workflow '{workflow_name}' step '{step_id}' action '{action}': {outcome}")


def validate_workflow_execution(selected_workflow: Optional[Dict[str, Any]]) -> Dict[str, Any]:
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
    return "continue" if next_step_id else "complete"


def handle_fetch_action(
    step: Dict[str, Any],
    current_step_id: str,
    steps: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]],
    extracted_fields: Dict[str, str],
    workflow_name: str = ""
) -> Dict[str, Any]:
    field_name = step.get("field", "")
    result = execute_fetch(step, conversation_history)
    
    if result.get("found"):
        # Field found - extract value and continue to next step
        extracted_fields[result["field_name"]] = result["value"]
        next_step_id = get_next_step_id(current_step_id, steps)
        status = determine_workflow_status(next_step_id)
        value_preview = str(result["value"])[:50] + "..." if len(str(result["value"])) > 50 else str(result["value"])
        _log_workflow_step(workflow_name, current_step_id, "fetch", f"succeeded to extract '{field_name}' from conversation history: {value_preview}")
    else:
        # Field not found - question was asked, wait for user input
        # Stay on the same step so it can be retried when new input arrives
        next_step_id = current_step_id
        status = "waiting_for_input"
        _log_workflow_step(workflow_name, current_step_id, "fetch", f"needs to get '{field_name}' from user (question asked)")
    
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
    extracted_fields: Dict[str, str],
    workflow_name: str = ""
) -> Dict[str, Any]:
    condition = step.get("condition", {})
    condition_result = evaluate_condition(condition, conversation_history, extracted_fields)
    
    next_step_id = get_next_step_id(current_step_id, steps, condition_result)
    status = determine_workflow_status(next_step_id)
    
    condition_str = str(condition).replace("\n", " ")[:100]
    _log_workflow_step(workflow_name, current_step_id, "conditional", f"condition evaluated to {condition_result}, next step: {next_step_id}")
    
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
    extracted_fields: Dict[str, str],
    workflow_name: str = ""
) -> Dict[str, Any]:
    reply = execute_reply(step, conversation_history, tone_config, extracted_fields)
    next_step_id = get_next_step_id(current_step_id, steps)
    
    # If there's a next step, wait for user input before continuing
    # (The next step might be a fetch that needs user response)
    if next_step_id:
        status = "waiting_for_input"
        _log_workflow_step(workflow_name, current_step_id, "reply", f"reply generated, waiting for user input, next step: {next_step_id}")
    else:
        # No next step - workflow is complete
        status = "complete"
        _log_workflow_step(workflow_name, current_step_id, "reply", "reply generated, workflow complete")
    
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
    tone_config: Dict[str, Any],
    workflow_name: str = ""
) -> Dict[str, Any]:
    tool_name = step.get("tool_name", "")
    execute_tool(step, conversation_history, tone_config)
    next_step_id = get_next_step_id(current_step_id, steps)
    status = determine_workflow_status(next_step_id)
    
    _log_workflow_step(workflow_name, current_step_id, "use_tool", f"executed tool '{tool_name}', next step: {next_step_id}")
    
    return build_step_result(
        status=status,
        next_step_id=next_step_id
    )


def handle_include_action(
    step: Dict[str, Any],
    current_step_id: str,
    steps: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]],
    tone_config: Dict[str, Any],
    workflow_name: str = ""
) -> Dict[str, Any]:
    reply = execute_include(step, conversation_history, tone_config)
    next_step_id = get_next_step_id(current_step_id, steps)
    
    # If there's a next step, wait for user input before continuing
    # (The next step might be a fetch that needs user response)
    if next_step_id:
        status = "waiting_for_input"
        _log_workflow_step(workflow_name, current_step_id, "include", f"included content, waiting for user input, next step: {next_step_id}")
    else:
        # No next step - workflow is complete
        status = "complete"
        _log_workflow_step(workflow_name, current_step_id, "include", "included content, workflow complete")
    
    return build_step_result(
        status=status,
        next_step_id=next_step_id,
        reply=reply
    )


def execute_workflow_step(prep_res: Dict[str, Any]) -> Dict[str, Any]:
    # Extract context
    selected_workflow = prep_res["selected_workflow"]
    current_step_id = prep_res["current_step"].get("step_id") if prep_res["current_step"] else None
    conversation_history = prep_res["conversation_history"]
    constants = prep_res["constants"]
    tone_config = prep_res["tone_config"]
    extracted_fields = prep_res["extracted_fields"]
    
    # Get workflow name for logging
    workflow_name = selected_workflow.get("name", "unknown") if selected_workflow else "none"
    
    # Validate workflow
    validation = validate_workflow_execution(selected_workflow)
    if not validation["valid"]:
        if _is_debugging_enabled():
            print(f"[DEBUG] workflow '{workflow_name}': {validation['status']}")
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
        if _is_debugging_enabled():
            print(f"[DEBUG] workflow '{workflow_name}': no step found, workflow complete")
        return build_step_result(
            status="complete",
            next_step_id=None
        )
    
    # Update current_step_id if it was None (initialized to first step)
    if not current_step_id:
        current_step_id = step.get("id")
    
    # Handle container steps (steps with nested steps but no action)
    # If this is a container step, automatically proceed to its first nested step
    if "steps" in step and not step.get("action"):
        nested_steps = step.get("steps", [])
        if nested_steps:
            first_nested_step_id = get_first_step_id(nested_steps)
            if first_nested_step_id:
                # Recursively process the first nested step
                # Update current_step_id to the first nested step
                current_step_id = first_nested_step_id
                # Get the nested step from registry
                step = step_registry.get(first_nested_step_id)
                if not step:
                    if _is_debugging_enabled():
                        print(f"[DEBUG] workflow '{workflow_name}': nested step '{first_nested_step_id}' not found in registry")
                    return build_step_result(
                        status="complete",
                        next_step_id=None
                    )
            else:
                # Container step with no nested steps - treat as complete
                if _is_debugging_enabled():
                    print(f"[DEBUG] workflow '{workflow_name}': container step '{current_step_id}' has no nested steps")
                return build_step_result(
                    status="complete",
                    next_step_id=None
                )
    
    # Check prerequisites if this is the first step
    check_and_handle_prerequisites(current_step_id, steps, constants, conversation_history)
    
    # Route to appropriate action handler
    action = step.get("action", "")
    
    if action == "fetch":
        return handle_fetch_action(
            step, current_step_id, steps, conversation_history, extracted_fields, workflow_name
        )
    elif action == "conditional":
        return handle_conditional_action(
            step, current_step_id, steps, conversation_history, extracted_fields, workflow_name
        )
    elif action == "reply":
        return handle_reply_action(
            step, current_step_id, steps, conversation_history, tone_config, extracted_fields, workflow_name
        )
    elif action == "use_tool":
        return handle_tool_action(
            step, current_step_id, steps, conversation_history, tone_config, workflow_name
        )
    elif action == "include":
        return handle_include_action(
            step, current_step_id, steps, conversation_history, tone_config, workflow_name
        )
    else:
        raise ValueError(f"unknown action type: '{action}' in step '{current_step_id}'")

