"""Utility functions for matching user input to workflows."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any
from utils.call_llm import call_llm
from utils.scenario_matcher import ScenarioMatcher


def grep_workflows(user_input: str, workflows: Dict[str, Dict[str, Any]]) -> List[str]:
    """
    Search workflows by matching 'when' field against user input using semantic similarity.
    
    Args:
        user_input: User's input text
        workflows: Dictionary of workflow definitions
    
    Returns:
        List of matching workflow names
    """
    # Extract all 'when' fields and corresponding workflow names
    when_scenarios = []
    workflow_names = []
    
    for workflow_name, workflow_def in workflows.items():
        when_text = workflow_def.get('when', '')
        if when_text:
            when_scenarios.append(when_text)
            workflow_names.append(workflow_name)
    
    if not when_scenarios:
        return []
    
    # Create matcher with all 'when' scenarios
    matcher = ScenarioMatcher(when_scenarios)
    
    # Match user input against scenarios with expanded candidate set
    # Increased k (15) to cast wider net - let LLM do final filtering
    # Lower min_score (0.25) to include more candidates, including those with lower semantic similarity
    # This ensures workflows like HandleQuoteRequest are included even if they score lower
    matches = matcher.match(user_input, k=15, min_score=0.25)
    
    # Map back to workflow names
    matched_workflows = []
    for scenario, score in matches:
        # Find the workflow name for this scenario
        idx = when_scenarios.index(scenario)
        matched_workflows.append(workflow_names[idx])
    
    return matched_workflows


def select_workflow_llm(user_input: str, candidate_workflows: Dict[str, Dict[str, Any]]) -> str:
    """
    Use LLM to select the most relevant workflow from candidates.
    
    Args:
        user_input: User's input text
        candidate_workflows: Dictionary of candidate workflow definitions
    
    Returns:
        Selected workflow name
    """
    # Format workflows for LLM - only include 'when' field
    workflows_text = []
    workflow_name_map = {}  # Map when text to workflow name
    for name, workflow_def in candidate_workflows.items():
        when_text = workflow_def.get('when', '')
        if when_text:
            workflows_text.append(f"- {when_text}")
            workflow_name_map[when_text] = name
    
    prompt = f"""Given the user input below, select the most relevant workflow from the candidates.

User Input: {user_input}

Available Workflows:
{chr(10).join(workflows_text)}

Respond with ONLY the 'when' text (exactly as shown above), nothing else."""

    response = call_llm(prompt).strip()
    
    # Map the 'when' text response back to workflow name
    if response in workflow_name_map:
        return workflow_name_map[response]
    
    # If LLM returned something else, try to find closest match by 'when' text
    for when_text, name in workflow_name_map.items():
        if when_text.lower() in response.lower() or response.lower() in when_text.lower():
            return name
    
    # Default to first candidate if no match found
    return list(candidate_workflows.keys())[0]

