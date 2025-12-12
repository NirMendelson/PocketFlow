"""Node for executing workflow steps."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pocketflow import Node
from utils.workflow_context import get_workflow_context
from utils.workflow_executor import execute_workflow_step


class ExecuteWorkflowNode(Node):
    """Node that executes workflow steps sequentially."""
    
    def prep(self, shared):
        """Get selected_workflow, current_step, conversation_history, and configs."""
        return get_workflow_context(shared)
    
    def exec(self, prep_res):
        """Execute current step using step ID."""
        return execute_workflow_step(prep_res)
    
    def post(self, shared, prep_res, exec_res):
        """Update current_step and extracted_fields."""
        if exec_res.get("status") == "complete":
            # Workflow complete
            shared["current_step"] = None
        elif exec_res.get("status") == "no_workflow":
            # No workflow matched
            shared["current_step"] = None
        else:
            # Update to next step ID
            next_step_id = exec_res.get("next_step_id")
            if next_step_id:
                shared["current_step"] = {"step_id": next_step_id}
            else:
                shared["current_step"] = None
        
        # Update extracted fields
        if "extracted_fields" in exec_res:
            shared["extracted_fields"] = exec_res["extracted_fields"]
        
        # Determine action for flow
        if exec_res.get("status") == "complete":
            return "complete"
        elif exec_res.get("status") == "no_workflow":
            return "default"
        elif exec_res.get("next_step_id"):
            # Continue executing workflow
            return "continue"
        else:
            return "default"

