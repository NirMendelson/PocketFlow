import json
from pocketflow import Node


class LoadBenchmarkNode(Node):
    
    def prep(self, shared):
        entry = shared.get("current_entry")
        return entry
    
    def exec(self, entry):
        return entry
    
    def post(self, shared, prep_res, exec_res):
        if exec_res:
            user_input = exec_res.get("input", "")
            shared["conversation_history"] = [
                {"role": "user", "content": user_input}
            ]
        return "default"

