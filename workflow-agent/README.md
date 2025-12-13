# Workflow-Based AI Agent

A simple AI agent built with PocketFlow that processes customer inquiries, matches them to workflows via grep search, and executes workflows with conditional branching.

## Overview

This agent:
1. Reads input from `benchmark/benchmark.json`
2. Searches workflows in `codebase/workflow.yaml` by matching the `when` field
3. If multiple workflows match, uses LLM (gpt-4o-mini) to select the most relevant
4. Executes the selected workflow step by step
5. Handles different action types: fetch, conditional, reply, use_tool, include
6. Maintains conversation history and tracks current workflow step

## Architecture

The agent uses a simple 3-node flow:
- **LoadBenchmarkNode**: Loads benchmark entries (BatchNode)
- **MatchWorkflowNode**: Matches user input to workflows
- **ExecuteWorkflowNode**: Executes workflow steps sequentially

## File Structure

```
workflow-agent/
├── main.py                 # Entry point
├── flow.py                 # Flow definition
├── nodes/
│   ├── __init__.py
│   ├── load_benchmark.py   # LoadBenchmarkNode
│   ├── match_workflow.py   # MatchWorkflowNode
│   └── execute_workflow.py # ExecuteWorkflowNode
├── utils/
│   ├── __init__.py
│   ├── litellm_configuration.py  # LiteLLM utility
│   ├── workflow_parser.py  # YAML parser
│   ├── workflow_matcher.py # Workflow matching
│   └── action_executor.py  # Action execution
├── requirements.txt
└── README.md
```

## Shared Store

The shared store contains minimal state:
- `conversation_history`: List of conversation messages
- `selected_workflow`: Selected workflow name and definition
- `current_step`: Current step ID, index, and branch info

## Installation

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file in the project root (PocketFlow directory):
```bash
cat > .env << EOF
LITELLM_MODEL=your_model_name_here
EOF
```

Or manually create `.env` file with:
```
LITELLM_MODEL=your_model_name_here
```

The `LITELLM_MODEL` should be in litellm format (e.g., `gpt-4o-mini`, `azure/gpt-4o-mini`, `anthropic/claude-3-5-sonnet-20241022`, etc.). See [litellm documentation](https://docs.litellm.ai/docs/providers) for supported models and configuration.

## Usage

1. Make sure virtual environment is activated:
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Run the agent:
```bash
python3 main.py
```

The agent will:
- Process each entry in `../benchmark/benchmark.json`
- Execute the appropriate workflow for each entry
- Save results to `../benchmark/benchmark-{timestamp}.json` with `agent_answer` field added to each entry

## Action Types

- **Fetch**: Extracts field from conversation or asks user
- **Conditional**: Evaluates condition and executes then/else branches
- **Reply**: Generates reply using message template and tone.yaml
- **Use Tool**: Executes tool (placeholder implementation)
- **Include**: Adds information/link to response

## Key Features

- Simple sequential step execution
- Conditional branching with nested steps
- LLM-based field extraction and condition evaluation
- Tone-aware reply generation
- Minimal shared state for clarity

