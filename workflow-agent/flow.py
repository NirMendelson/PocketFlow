"""Flow definition for workflow agent."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pocketflow import Flow
from nodes.load_benchmark import LoadBenchmarkNode
from nodes.match_workflow import MatchWorkflowNode
from nodes.execute_workflow import ExecuteWorkflowNode


def create_workflow_flow():
    """Create and return the workflow agent flow."""
    # Create nodes
    load_benchmark = LoadBenchmarkNode()
    match_workflow = MatchWorkflowNode()
    execute_workflow = ExecuteWorkflowNode()
    
    # Connect nodes in sequence
    load_benchmark >> match_workflow >> execute_workflow
    
    # Execute workflow can loop back to itself to continue steps
    execute_workflow - "continue" >> execute_workflow
    
    # Create flow starting with load_benchmark
    return Flow(start=load_benchmark)

