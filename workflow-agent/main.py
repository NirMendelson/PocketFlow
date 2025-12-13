"""Main entry point for workflow agent."""

import os
# Set TOKENIZERS_PARALLELISM before any tokenizer imports to suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import json
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load .env file from project root (PocketFlow directory, parent of workflow-agent)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from utils.workflow_parser import load_workflows, load_constants, load_tools
from flow import create_workflow_flow


def main():
    """Main function to process benchmark entries."""
    # Load YAML files
    base_path = "../codebase"
    workflows = load_workflows(f"{base_path}/workflow.yaml")
    constants = load_constants(f"{base_path}/constants.yaml")
    tools = load_tools(f"{base_path}/tools.yaml")
    tone_config = load_constants(f"{base_path}/tone.yaml")
    
    # Load benchmark
    benchmark_path = "../benchmark/benchmark.json"
    with open(benchmark_path, 'r', encoding='utf-8') as f:
        benchmark_entries = json.load(f)
    
    # Create flow
    flow = create_workflow_flow()
    
    # Process each benchmark entry separately
    results = []
    
    for entry in benchmark_entries:
        print(f"\n{'='*60}")
        print(f"Processing entry {entry.get('id', 'unknown')}")
        print(f"Input: {entry.get('input', '')[:100]}...")
        print(f"{'='*60}\n")
        
        # Initialize shared store for this entry
        shared = {
            "conversation_history": [],
            "selected_workflow": None,
            "current_step": {
                "step_id": None,
                "step_index": 0,
                "branch": None
            },
            "workflows": workflows,
            "constants": constants,
            "tools": tools,
            "tone_config": tone_config,
            "extracted_fields": {},
            "benchmark_path": benchmark_path,
            "current_entry": entry
        }
        
        # Initialize agent_answer
        agent_answer = ""
        
        # Run flow
        try:
            flow.run(shared)
            
            # Extract agent answer from conversation history (last assistant message)
            conversation_history = shared.get("conversation_history", [])
            for msg in reversed(conversation_history):
                if msg.get("role") == "assistant":
                    agent_answer = msg.get("content", "")
                    break
            
            # Print results
            selected_workflow = shared.get('selected_workflow')
            workflow_name = selected_workflow.get('name', 'None') if selected_workflow else 'None'
            print(f"\nSelected Workflow: {workflow_name}")
            print(f"\nAgent Answer: {agent_answer[:200]}...")
            print(f"\nExpected Answer: {entry.get('expected_answer', '')[:200]}...")
            
        except Exception as e:
            print(f"error processing entry {entry.get('id')}: {e}")
            import traceback
            traceback.print_exc()
            agent_answer = f"Error: {str(e)}"
        
        # Add agent_answer to entry and store result
        result_entry = entry.copy()
        result_entry["agent_answer"] = agent_answer
        results.append(result_entry)
    
    # Save results to timestamped JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"../benchmark/benchmark-{timestamp}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Results saved to: {output_path}")
    print(f"Processed {len(results)} entries")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

