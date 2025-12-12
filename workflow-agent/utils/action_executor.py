"""Action executor utilities for handling different workflow action types."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any, Optional
import yaml
from utils.call_llm import call_llm


def execute_fetch(step: Dict[str, Any], conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Execute a fetch action: extract field from conversation or ask user.
    
    Args:
        step: Step definition with 'field' key
        conversation_history: List of conversation messages
    
    Returns:
        Dictionary with 'field_name', 'value' (if found), and 'question' (if not found)
    """
    field_name = step.get('field', '')
    
    # Format conversation for LLM
    conv_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
    
    prompt = f"""Read the conversation carefully and check if you have the field '{field_name}' in the conversation.

Conversation:
{conv_text}

If the field '{field_name}' is present in the conversation, extract it and return ONLY the value.
If the field '{field_name}' is NOT present, generate a natural, friendly question to ask the user for this information.

Respond in this format:
```yaml
found: true/false
value: <extracted value if found>
question: <question to ask if not found>
```"""

    response = call_llm(prompt)
    
    # Parse YAML response
    try:
        yaml_start = response.find('```yaml')
        yaml_end = response.find('```', yaml_start + 7)
        if yaml_start != -1 and yaml_end != -1:
            yaml_str = response[yaml_start + 7:yaml_end].strip()
            result = yaml.safe_load(yaml_str)
        else:
            # Try to parse without code fences
            result = yaml.safe_load(response)
        
        found = result.get('found', False) if isinstance(result, dict) else False
        value = result.get('value', '') if isinstance(result, dict) else ''
        question = result.get('question', '') if isinstance(result, dict) else ''
        
        if not found and question:
            # Add question to conversation history
            conversation_history.append({
                "role": "assistant",
                "content": question
            })
        
        return {
            "field_name": field_name,
            "found": found,
            "value": value,
            "question": question
        }
    except Exception as e:
        print(f"error parsing fetch response: {e}")
        # Fallback: ask for the field
        question = f"Could you please provide your {field_name}?"
        conversation_history.append({
            "role": "assistant",
            "content": question
        })
        return {
            "field_name": field_name,
            "found": False,
            "value": "",
            "question": question
        }


def evaluate_condition(condition: Dict[str, Any], conversation_history: List[Dict[str, str]], extracted_fields: Dict[str, str]) -> bool:
    """
    Evaluate a condition using LLM.
    
    Args:
        condition: Condition definition with operator, left, right, etc.
        conversation_history: List of conversation messages
        extracted_fields: Dictionary of extracted field values
    
    Returns:
        True or False
    """
    # Format conversation and fields for LLM
    conv_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
    fields_text = "\n".join([f"{k}: {v}" for k, v in extracted_fields.items()])
    
    # Format condition for LLM
    operator = condition.get('operator', '')
    left = condition.get('left', '')
    right = condition.get('right', '')
    field = condition.get('field', '')
    
    prompt = f"""Evaluate this condition based on the conversation and extracted fields.

Condition:
- Operator: {operator}
- Left: {left}
- Right: {right}
- Field: {field}

Conversation:
{conv_text}

Extracted Fields:
{fields_text}

Evaluate the condition and return ONLY "true" or "false" (lowercase, no quotes, no explanation)."""

    response = call_llm(prompt).strip().lower()
    
    return response == "true"


def execute_reply(step: Dict[str, Any], conversation_history: List[Dict[str, str]], tone_config: Dict[str, Any], extracted_fields: Dict[str, str]) -> str:
    """
    Execute a reply action: generate reply using message template and tone.yaml.
    
    Args:
        step: Step definition with 'message' key
        conversation_history: List of conversation messages
        tone_config: Tone configuration from tone.yaml
        extracted_fields: Dictionary of extracted field values
    
    Returns:
        Generated reply message
    """
    message_template = step.get('message', '')
    
    # Replace template variables with extracted values
    for field_name, field_value in extracted_fields.items():
        message_template = message_template.replace(f"{{{{ {field_name} }}}}", str(field_value))
        message_template = message_template.replace(f"{{{{{ {field_name} }}}}}", str(field_value))
    
    # Format tone config for prompt
    identity = tone_config.get('identity', {})
    tone_list = tone_config.get('tone', [])
    guidelines = tone_config.get('guidelines', [])
    
    tone_text = "\n".join([f"- {t}" for t in tone_list])
    guidelines_text = "\n".join([f"- {g}" for g in guidelines])
    
    prompt = f"""You are an AI assistant providing support.

Identity:
- Role: {identity.get('role', 'AI assistant')}
- Positioning: {identity.get('positioning', 'helpful companion')}

Tone Guidelines:
{tone_text}

Additional Guidelines:
{guidelines_text}

Generate a reply message based on this template: {message_template}

Conversation context:
{chr(10).join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-3:]])}

Generate a natural, friendly reply that follows the tone guidelines. Return ONLY the reply message, nothing else."""

    reply = call_llm(prompt).strip()
    
    # Add reply to conversation history
    conversation_history.append({
        "role": "assistant",
        "content": reply
    })
    
    return reply


def execute_tool(step: Dict[str, Any], conversation_history: Optional[List[Dict[str, str]]] = None, tone_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a tool action.
    
    Args:
        step: Step definition with 'tool_name' and 'reason' keys
        conversation_history: List of conversation messages (optional)
        tone_config: Tone configuration from tone.yaml (optional)
    
    Returns:
        Dictionary with tool execution result
    """
    tool_name = step.get('tool_name', '')
    reason = step.get('reason', '')
    
    # Placeholder implementation
    print(f"executing tool: {tool_name}, reason: {reason}")
    
    # If escalation tool, generate a message about transferring to human agent
    if tool_name == "escalation" and conversation_history is not None and tone_config is not None:
        # Generate escalation message using LLM with tone guidelines
        identity = tone_config.get('identity', {})
        tone_list = tone_config.get('tone', [])
        guidelines = tone_config.get('guidelines', [])
        
        tone_text = "\n".join([f"- {t}" for t in tone_list])
        guidelines_text = "\n".join([f"- {g}" for g in guidelines])
        
        prompt = f"""You are an AI assistant providing support.

Identity:
- Role: {identity.get('role', 'AI assistant')}
- Positioning: {identity.get('positioning', 'helpful companion')}

Tone Guidelines:
{tone_text}

Additional Guidelines:
{guidelines_text}

You need to inform the user that you are escalating their request to a human agent for review and approval.

Reason for escalation: {reason}

Conversation context:
{chr(10).join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-3:]])}

Generate a natural, friendly message informing the user that you're escalating/transferring their request to a human agent. Use phrases like "I'll need to escalate your request" or "I'm transferring you to a human agent". Return ONLY the message, nothing else."""

        escalation_message = call_llm(prompt).strip()
        
        # Add escalation message to conversation history
        conversation_history.append({
            "role": "assistant",
            "content": escalation_message
        })
    
    return {
        "tool_name": tool_name,
        "reason": reason,
        "executed": True
    }


def execute_include(step: Dict[str, Any]) -> str:
    """
    Execute an include action: add information/link.
    
    Args:
        step: Step definition with 'information' key
    
    Returns:
        Information string
    """
    information = step.get('information', '')
    
    return information

