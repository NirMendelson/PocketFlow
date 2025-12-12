"""Utility functions for parsing YAML workflow files."""

import yaml
from typing import Dict, List, Any


def load_workflows(path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load and parse workflow.yaml file.
    
    Args:
        path: Path to workflow.yaml file
    
    Returns:
        Dictionary mapping workflow names to their definitions
    """
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by '---' separator to get individual workflows
    workflow_sections = content.split('---')
    
    workflows = {}
    
    for section in workflow_sections:
        section = section.strip()
        if not section or section.startswith('#'):
            continue
        
        try:
            workflow_data = yaml.safe_load(section)
            if workflow_data and 'workflow' in workflow_data:
                workflow_name = workflow_data['workflow']
                workflows[workflow_name] = workflow_data
        except yaml.YAMLError as e:
            print(f"error parsing workflow section: {e}")
            continue
    
    return workflows


def load_constants(path: str) -> Dict[str, Any]:
    """
    Load and parse constants.yaml file.
    
    Args:
        path: Path to constants.yaml file
    
    Returns:
        Dictionary with constants configuration
    """
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def load_tools(path: str) -> Dict[str, Any]:
    """
    Load and parse tools.yaml file.
    
    Args:
        path: Path to tools.yaml file
    
    Returns:
        Dictionary with tools configuration
    """
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


if __name__ == "__main__":
    # Test parsing
    workflows = load_workflows("../codebase/workflow.yaml")
    print(f"loaded {len(workflows)} workflows")
    for name in list(workflows.keys())[:3]:
        print(f"  - {name}")

