"""Utility functions for building step registries from workflow definitions."""

from typing import Dict, List, Any, Optional, Tuple


def build_step_registry(steps: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Build a flat registry mapping step IDs to step definitions.
    
    Recursively traverses the workflow structure including nested steps
    in conditional branches.
    
    Args:
        steps: List of step definitions from workflow
        
    Returns:
        Dictionary mapping step_id to step definition
    """
    registry = {}
    
    def _process_step(step: Dict[str, Any], parent_id: Optional[str] = None):
        """Recursively process a step and its branches."""
        step_id = step.get("id")
        if not step_id:
            return
        
        # Store the step in registry
        registry[step_id] = step.copy()
        
        # Process conditional branches
        if step.get("action") == "conditional":
            # Process then branch
            then_branch = step.get("then")
            if then_branch:
                if isinstance(then_branch, list):
                    # Multiple steps in then branch
                    for branch_step in then_branch:
                        _process_step(branch_step, step_id)
                else:
                    # Single action in then branch
                    if then_branch.get("id"):
                        _process_step(then_branch, step_id)
            
            # Process else branch
            else_branch = step.get("else")
            if else_branch:
                if isinstance(else_branch, list):
                    # Multiple steps in else branch
                    for branch_step in else_branch:
                        _process_step(branch_step, step_id)
                else:
                    # Single action in else branch
                    if else_branch.get("id"):
                        _process_step(else_branch, step_id)
        
        # Process nested steps (for steps arrays in branches)
        if "steps" in step:
            for nested_step in step["steps"]:
                _process_step(nested_step, step_id)
    
    # Process all top-level steps
    for step in steps:
        _process_step(step)
    
    return registry


def get_next_step_id(
    current_step_id: str,
    steps: List[Dict[str, Any]],
    condition_result: Optional[bool] = None
) -> Optional[str]:
    """
    Determine the next step ID after executing the current step.
    
    Args:
        current_step_id: ID of the step that was just executed
        steps: Original list of top-level steps
        condition_result: Result of condition evaluation (for conditional steps)
        
    Returns:
        Next step ID, or None if workflow is complete
    """
    def _find_step_and_get_next(step_id: str, step_list: List[Dict[str, Any]], 
                                 top_level_steps: List[Dict[str, Any]],
                                 conditional_step_idx: Optional[int] = None) -> Optional[str]:
        """Recursively find step and determine next step."""
        for idx, step in enumerate(step_list):
            step_step_id = step.get("id")
            
            # Found the current step
            if step_step_id == step_id:
                # Check if there's a next step in the same list
                if idx + 1 < len(step_list):
                    return step_list[idx + 1].get("id")
                # If we're in a branch, return next step after parent conditional
                if conditional_step_idx is not None:
                    # Find the parent conditional in top-level steps
                    if conditional_step_idx + 1 < len(top_level_steps):
                        return top_level_steps[conditional_step_idx + 1].get("id")
                return None
            
            # Check conditional branches
            if step.get("action") == "conditional":
                conditional_idx = None
                # Find this conditional in top-level steps
                for top_idx, top_step in enumerate(top_level_steps):
                    if top_step.get("id") == step.get("id"):
                        conditional_idx = top_idx
                        break
                
                # Check then branch
                then_branch = step.get("then")
                if then_branch:
                    if isinstance(then_branch, list):
                        result = _find_step_and_get_next(step_id, then_branch, top_level_steps, conditional_idx)
                        if result is not None:
                            return result
                    elif then_branch.get("id") == step_id:
                        # Single action in then - next is after conditional
                        if conditional_idx is not None and conditional_idx + 1 < len(top_level_steps):
                            return top_level_steps[conditional_idx + 1].get("id")
                        return None
                
                # Check else branch
                else_branch = step.get("else")
                if else_branch:
                    if isinstance(else_branch, list):
                        result = _find_step_and_get_next(step_id, else_branch, top_level_steps, conditional_idx)
                        if result is not None:
                            return result
                    elif else_branch.get("id") == step_id:
                        # Single action in else - next is after conditional
                        if conditional_idx is not None and conditional_idx + 1 < len(top_level_steps):
                            return top_level_steps[conditional_idx + 1].get("id")
                        return None
            
            # Check nested steps (for steps arrays in branches)
            if "steps" in step:
                result = _find_step_and_get_next(step_id, step["steps"], top_level_steps, conditional_step_idx)
                if result is not None:
                    return result
        
        return None
    
    # For conditional steps, return first step in the selected branch
    for idx, step in enumerate(steps):
        if step.get("id") == current_step_id and step.get("action") == "conditional":
            if condition_result is True:
                then_branch = step.get("then")
                if then_branch:
                    if isinstance(then_branch, list) and len(then_branch) > 0:
                        return then_branch[0].get("id")
                    elif then_branch.get("id"):
                        return then_branch.get("id")
            else:
                else_branch = step.get("else")
                if else_branch:
                    if isinstance(else_branch, list) and len(else_branch) > 0:
                        return else_branch[0].get("id")
                    elif else_branch.get("id"):
                        return else_branch.get("id")
            # No branch selected, continue after conditional
            if idx + 1 < len(steps):
                return steps[idx + 1].get("id")
            return None
    
    # For other steps, find them in the structure
    return _find_step_and_get_next(current_step_id, steps, steps)


def get_first_step_id(steps: List[Dict[str, Any]]) -> Optional[str]:
    """Get the ID of the first step in the workflow."""
    if not steps:
        return None
    return steps[0].get("id")

