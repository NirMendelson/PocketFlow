# Flow definition for workflow agent

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pocketflow import Flow
from nodes.load_benchmark import LoadBenchmarkNode
from nodes.match_workflow import MatchWorkflowNode
from nodes.execute_workflow import ExecuteWorkflowNode


# Create and return the workflow agent flow
def create_workflow_flow():
    # Create nodes
    load_benchmark = LoadBenchmarkNode()
    match_workflow = MatchWorkflowNode()
    execute_workflow = ExecuteWorkflowNode()
    
    # Connect nodes in sequence
    load_benchmark >> match_workflow
    
    # If workflow matched, execute it
    match_workflow - "default" >> execute_workflow
    
    # If clarification needed, don't execute workflow (flow ends)
    # The clarification question is already in conversation_history
    # No transition needed for "clarify" - flow ends naturally
    
    # Execute workflow can loop back to itself to continue steps
    execute_workflow - "continue" >> execute_workflow
    
    # When workflow completes or no workflow, flow ends naturally
    # No transitions needed for None or "default" - flow ends
    
    # Create flow starting with load_benchmark
    return Flow(start=load_benchmark)

