import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any, Optional
import yaml
from utils.litellm_configuration import call_litellm

# This file contains the functions to execute the different actions in the workflow- Fetch, Conditional, Reply, Use Tool, Include


def _is_debugging_enabled():
    """Check if DEBUGGING_MODE is enabled from environment variables."""
    return os.environ.get("DEBUGGING_MODE", "").lower() in ("true", "1", "yes")


def execute_fetch(step: Dict[str, Any], conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    field_name = step.get('field', '')
    
    # Format conversation for LLM
    conv_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
    
    prompt = f"""You are an intelligence agent. You have great capabilities to read between the lines and infer information. Read the conversation carefully and check if you have the field '{field_name}' in the conversation, or can infer it from the conversation.


You should infer information whenever possible, even if it is only implied indirectly.
Treat the conversation like a detective: if a human could reasonably infer the answer, you should too.

TASK:
1. Check if the information for this field was mentioned in the conversation history
2. You are intelligence agent. Think like a human reading between the lines: infer information whenever it is implied, even if not stated directly.
3. PRIORITY:
   (1) Prefer explicit statements.
   (2) If not explicit, infer the value from context if a reasonable human would.
   (3) Only if it is neither explicit nor inferable, ask the user for this specific missing information.
4. Normalize the user's meaning into the most appropriate value for this field — the wording does not need to match exactly.

EXAMPLES OF INFERENCE:
- "I sent the package yesterday." → They have a tracking number or proof of shipment.
- "I'll reboot the server." → They have admin access to that server.
- "I'll check the security camera." → They have a camera system installed.
- "The landlord raised the price again." → They're renting (not owning).
- "I'm not been able to enter the YouTube app, and the rest of my apps work fine." → They have a problem with the YouTube app and its not a WIFI or hardware issue, because the rest work well.


Conversation:
{conv_text}


Respond in this format:
```yaml
found: true/false
value: <extracted value if found>
question: <question to ask if not found>
```"""

    if _is_debugging_enabled():
        print(f"[DEBUG] fetch prompt:\n{prompt}\n")
    
    response = call_litellm(prompt)
    
    if _is_debugging_enabled():
        print(f"[DEBUG] fetch response:\n{response}\n")
    
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
        
        result_dict = {
            "field_name": field_name,
            "found": found,
            "value": value,
            "question": question
        }
        if _is_debugging_enabled():
            print(f"[DEBUG] fetch result: {result_dict}\n")
        return result_dict
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


def execute_fetch_with_condition(
    fetch_step: Dict[str, Any],
    condition_step: Dict[str, Any],
    conversation_history: List[Dict[str, str]],
    extracted_fields: Dict[str, str]
) -> Dict[str, Any]:
    """
    Combined fetch and condition evaluation in a single LLM prompt.
    This is more efficient when fetch is immediately followed by a condition check.
    """
    field_name = fetch_step.get('field', '')
    condition = condition_step.get('condition', {})
    
    # Format conversation for LLM
    conv_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
    
    # Format condition for LLM
    operator = condition.get('operator', '')
    left = condition.get('left', '')
    right = condition.get('right', '')
    field = condition.get('field', '')
    
    # Extract field name from template variable in left if it's a template
    field_name_from_left = None
    left_str = str(left).strip()
    if left_str.startswith("{{") and left_str.endswith("}}"):
        # Extract field name from template like "{{ field_name }}"
        field_name_from_left = left_str.replace("{{", "").replace("}}", "").strip()
    
    # Resolve template variables in left and right (using already extracted fields)
    resolved_left = str(left)
    for field_name_existing, field_val in extracted_fields.items():
        resolved_left = resolved_left.replace(f"{{{{ {field_name_existing} }}}}", str(field_val))
        resolved_left = resolved_left.replace(f"{{{{{ {field_name_existing} }}}}}", str(field_val))
        right = str(right).replace(f"{{{{ {field_name_existing} }}}}", str(field_val))
        right = str(right).replace(f"{{{{{ {field_name_existing} }}}}}", str(field_val))
    
    # Determine the field name and value to display
    # If the condition references the field we're fetching, use the field name
    # Otherwise use the resolved left side
    if field_name_from_left == field_name or field == field_name:
        # Condition references the field we're fetching
        display_field_name = field_name
        condition_str = f"{display_field_name} {operator} {right}"
    elif field:
        display_field_name = field
        condition_str = f"{display_field_name} {operator} {right}"
    else:
        condition_str = f"{resolved_left} {operator} {right}"
    
    prompt = f"""You are an intelligence agent. You have great capabilities to read between the lines and infer information. 

TASK 1: FETCH FIELD
Read the conversation carefully and check if you have the field '{field_name}' in the conversation, or can infer it from the conversation.

You should infer information whenever possible, even if it is only implied indirectly.
Treat the conversation like a detective: if a human could reasonably infer the answer, you should too.

PRIORITY:
(1) Prefer explicit statements.
(2) If not explicit, infer the value from context if a reasonable human would.
(3) Only if it is neither explicit nor inferable, ask the user for this specific missing information.

Normalize the user's meaning into the most appropriate value for this field — the wording does not need to match exactly.

EXAMPLES OF INFERENCE:
- "I sent the package yesterday." → They have a tracking number or proof of shipment.
- "I'll reboot the server." → They have admin access to that server.
- "I'll check the security camera." → They have a camera system installed.
- "The landlord raised the price again." → They're renting (not owning).
- "I'm not been able to enter the YouTube app, and the rest of my apps work fine." → They have a problem with the YouTube app and its not a WIFI or hardware issue, because the rest work well.

TASK 2: EVALUATE CONDITION (only if field is found)
If you found the field '{field_name}' in TASK 1, now evaluate this condition: {condition_str}

IMPORTANT INSTRUCTIONS FOR CONDITION EVALUATION:
- The condition "{condition_str}" may reference the field '{field_name}' that you just extracted.
- Use the actual value you extracted for '{field_name}' in TASK 1 when evaluating the condition.
- If the condition contains "{{ {field_name} }}", replace it with the value you found.
- Use your intelligence to determine if the condition is true or false, don't do a simple string comparison.
- Examples: California = CA is true, yes = yeah = I think so = any other phrase with basic meaning of yes

Conversation:
{conv_text}

Respond in this format:
```yaml
found: true/false
value: <extracted value if found>
question: <question to ask if not found>
condition_result: <true/false if found, null if not found>
```"""

    if _is_debugging_enabled():
        print(f"[DEBUG] fetch_with_condition prompt:\n{prompt}\n")
    
    response = call_litellm(prompt)
    
    if _is_debugging_enabled():
        print(f"[DEBUG] fetch_with_condition response:\n{response}\n")
    
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
        condition_result = result.get('condition_result') if isinstance(result, dict) else None
        
        # Convert condition_result to boolean if it's a string
        if isinstance(condition_result, str):
            condition_result = condition_result.lower() == "true"
        elif condition_result is None:
            condition_result = None
        
        if not found and question:
            # Add question to conversation history
            conversation_history.append({
                "role": "assistant",
                "content": question
            })
        
        result_dict = {
            "field_name": field_name,
            "found": found,
            "value": value,
            "question": question,
            "condition_result": condition_result
        }
        if _is_debugging_enabled():
            print(f"[DEBUG] fetch_with_condition result: {result_dict}\n")
        return result_dict
    except Exception as e:
        print(f"error parsing fetch_with_condition response: {e}")
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
            "question": question,
            "condition_result": None
        }


def evaluate_condition(condition: Dict[str, Any], conversation_history: List[Dict[str, str]], extracted_fields: Dict[str, str]) -> bool:
    # Format conversation for LLM
    conv_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
    
    # Format condition for LLM
    operator = condition.get('operator', '')
    left = condition.get('left', '')
    right = condition.get('right', '')
    field = condition.get('field', '')
    
    # Extract field name from template variable in left if it's a template
    field_name_from_left = None
    left_str = str(left).strip()
    if left_str.startswith("{{") and left_str.endswith("}}"):
        # Extract field name from template like "{{ field_name }}"
        field_name_from_left = left_str.replace("{{", "").replace("}}", "").strip()
    
    # Resolve template variables in left and right
    resolved_left = str(left)
    for field_name, field_val in extracted_fields.items():
        resolved_left = resolved_left.replace(f"{{{{ {field_name} }}}}", str(field_val))
        resolved_left = resolved_left.replace(f"{{{{{ {field_name} }}}}}", str(field_val))
        right = str(right).replace(f"{{{{ {field_name} }}}}", str(field_val))
        right = str(right).replace(f"{{{{{ {field_name} }}}}}", str(field_val))
    
    # Determine the field name and value to display
    display_field_name = field or field_name_from_left
    field_value = None
    if display_field_name and display_field_name in extracted_fields:
        field_value = extracted_fields[display_field_name]
    elif field_name_from_left and field_name_from_left in extracted_fields:
        field_value = extracted_fields[field_name_from_left]
    
    # Build condition string and field info
    if display_field_name and field_value is not None:
        condition_str = f"{display_field_name} {operator} {right}"
        field_info = f"Field '{display_field_name}' has value: {field_value}"
    else:
        condition_str = f"{resolved_left} {operator} {right}"
        field_info = f"Left side value: {resolved_left}"
    
    prompt = f"""You are an intelligence agent. Evaluate this condition based on the field value and conversation context.

{field_info}

Condition to evaluate: {condition_str}

Conversation history (for context):
{conv_text}

TASK: Determine if the condition "{condition_str}" is true or false.

CRITICAL: Use your intelligence to determine if the condition is true or false, don't do a simple string comparison.
- California = CA is true
- yes = yeah = I think so = any other phrase with basic meaning of yes


Evaluate the condition and return ONLY "true" or "false" (lowercase, no quotes, no explanation)."""

    if _is_debugging_enabled():
        print(f"[DEBUG] condition prompt:\n{prompt}\n")
    
    response = call_litellm(prompt).strip().lower()
    
    if _is_debugging_enabled():
        print(f"[DEBUG] condition response: {response}\n")
    
    result = response == "true"
    
    if _is_debugging_enabled():
        print(f"[DEBUG] condition result: {result}\n")
    
    return result


def execute_reply(step: Dict[str, Any], conversation_history: List[Dict[str, str]], tone_config: Dict[str, Any], extracted_fields: Dict[str, str]) -> str:
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

    reply = call_litellm(prompt).strip()
    
    # Add reply to conversation history
    conversation_history.append({
        "role": "assistant",
        "content": reply
    })
    
    return reply


def execute_tool(step: Dict[str, Any], conversation_history: Optional[List[Dict[str, str]]] = None, tone_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

        escalation_message = call_litellm(prompt).strip()
        
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


def execute_include(step: Dict[str, Any], conversation_history: List[Dict[str, str]], tone_config: Dict[str, Any]) -> str:
    information = step.get('information', '')
    
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

The user has asked a question, and you need to provide a helpful response that includes this information/link: {information}

Conversation context:
{chr(10).join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-3:]])}

Generate a natural, friendly reply that:
1. Acknowledges the user's question/concern
2. Includes the information/link naturally in your response
3. Follows the tone guidelines

Return ONLY the reply message, nothing else."""

    reply = call_litellm(prompt).strip()
    
    # Add reply to conversation history
    conversation_history.append({
        "role": "assistant",
        "content": reply
    })
    
    return reply

