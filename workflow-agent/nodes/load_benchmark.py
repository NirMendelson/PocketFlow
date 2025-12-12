"""Node for loading benchmark entries."""

import json
from pocketflow import Node


class LoadBenchmarkNode(Node):
    """Node that loads a single benchmark entry and initializes conversation history."""
    
    def prep(self, shared):
        """Get the entry to process."""
        entry = shared.get("current_entry")
        return entry
    
    def exec(self, entry):
        """Return entry data."""
        return entry
    
    def post(self, shared, prep_res, exec_res):
        """Initialize conversation_history with user input."""
        if exec_res:
            user_input = exec_res.get("input", "")
            shared["conversation_history"] = [
                {"role": "user", "content": user_input}
            ]
        return "default"

