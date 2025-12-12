"""Node for matching user input to workflows."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pocketflow import Node
from utils.workflow_matcher import grep_workflows, select_workflow_llm


def _is_debugging_enabled():
    """Check if DEBUGGING_MODE is enabled from environment variables."""
    return os.environ.get("DEBUGGING_MODE", "").lower() in ("true", "1", "yes")


class MatchWorkflowNode(Node):
    """Node that matches user input to workflows via grep search and LLM selection."""
    
    def prep(self, shared):
        """Get user input from conversation_history and workflows."""
        conversation_history = shared.get("conversation_history", [])
        workflows = shared.get("workflows", {})
        
        # Get user input (first user message)
        user_input = ""
        for msg in conversation_history:
            if msg.get("role") == "user":
                user_input = msg.get("content", "")
                break
        
        return user_input, workflows
    
    def exec(self, prep_res):
        """Grep search workflows, LLM select if multiple."""
        user_input, workflows = prep_res
        
        if not workflows:
            return None
        
        # Grep search on 'when' fields
        matches = grep_workflows(user_input, workflows)
        
        # Debug: show matched workflows
        if _is_debugging_enabled():
            if len(matches) == 0:
                print(f"[DEBUG] grep search found 0 matching workflows")
            else:
                print(f"[DEBUG] grep search found {len(matches)} matching workflow(s): {', '.join(matches)}")
        
        if len(matches) == 0:
            return None
        elif len(matches) == 1:
            return matches[0]
        else:
            # Multiple matches - use LLM to select best one
            candidate_workflows = {name: workflows[name] for name in matches}
            selected = select_workflow_llm(user_input, candidate_workflows)
            
            # Debug: show LLM selection
            if _is_debugging_enabled():
                print(f"[DEBUG] LLM selected workflow: '{selected}' from {len(matches)} candidates")
            
            return selected
    
    def post(self, shared, prep_res, exec_res):
        """Store selected_workflow."""
        if exec_res is None:
            # No workflow matched
            shared["selected_workflow"] = None
            if _is_debugging_enabled():
                print(f"[DEBUG] no workflow selected (no matches found)")
            return "default"
        
        workflows = shared.get("workflows", {})
        workflow_name = exec_res
        
        shared["selected_workflow"] = {
            "name": workflow_name,
            "definition": workflows.get(workflow_name, {})
        }
        
        # Debug: show final selected workflow
        if _is_debugging_enabled():
            workflow_def = workflows.get(workflow_name, {})
            when_text = workflow_def.get('when', 'N/A')
            print(f"[DEBUG] selected workflow: '{workflow_name}' (when: {when_text})")
        
        return "default"

