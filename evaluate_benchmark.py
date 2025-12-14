"""Evaluate benchmark results using litellm."""

import os
import json
import yaml
import re
import sys
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# Add workflow-agent to path to import litellm_configuration
sys.path.insert(0, str(Path(__file__).parent / "workflow-agent"))
from utils.litellm_configuration import call_litellm


def find_latest_benchmark_file(benchmark_dir: str = "benchmark") -> str | None:
    """
    Find the latest benchmark-{timestamp}.json file.
    
    Args:
        benchmark_dir: Directory containing benchmark files
        
    Returns:
        Path to the latest benchmark file, or None if not found
    """
    benchmark_path = Path(benchmark_dir)
    if not benchmark_path.exists():
        return None
    
    # Find all benchmark-{timestamp}.json files
    benchmark_files = list(benchmark_path.glob("benchmark-*.json"))
    
    if not benchmark_files:
        return None
    
    # Sort by modification time (newest first)
    benchmark_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    return str(benchmark_files[0])


def evaluate_agent_output(
    input_text: str,
    instruction: str,
    agent_output: str,
    expected_answer: str | None = None
) -> Dict[str, Any]:
    """
    Evaluate if the agent output follows the instruction using litellm.

    Args:
        input_text: The customer query/input
        instruction: The instruction that should be followed
        agent_output: The response agent's output
        expected_answer: The expected/correct answer (optional)

    Returns:
        dict with 'passed' (bool) and 'reason' (str)
    """
    load_dotenv()
    
    prompt = f"""You are evaluating if an AI agent followed instructions correctly. You don't care about details, only in the answer is close to the expected one, and doesn't go against the instruction.

Instruction:
{instruction}

Expected Answer:
{expected_answer}

Agent Output:
{agent_output}

Evaluate if the agent followed the instruction and provided an answer close enough to the expected one.

Critical Rule:
1. Escalating means that the agent need to say that he is escalating, it doesn't matter the exact wording, the main thing is that you can infer from it that the agent is escalating (e.g., "I'll need to escalate it", "I'll escalate this", "I'm escalating your request", "I'm connecting you with a human agent", "I transfer this to a human agent").

2. When To Pass:
- If tone is different between the expected answer and the agent answer, but the core logic is close enough.
- If the agent answer has more information than the expected answer, but the core logic is close enough.
- If the agent answer has less information than the expected answer, but the core logic is close enough.
- If the agent answer is different from the expected answer, but the core logic is close enough.
- If the agent doesn't follow the instructions entirely, but its close enough to the expected answer.
- If the agent answer doesn't contain a piece of information that is not relevant for example:
    - the agent answer doesn't contain the international phone number for customers calling from outside US/Canada.
    - the agent answer doesn't contain information for states that is not relevant for the user state.

3. When To Fail:
- ONLY if the agent answer is completly different from the expected answer and completly ignore the instruction.

4. If the agent answer is close but not totally accurate, pass it.

Return your evaluation in YAML format:

```yaml
passed: true/false
reason: |
  Your explanation of why it passed or failed
```"""

    try:
        response_text = call_litellm(prompt)
        
        # Extract YAML from response
        yaml_match = re.search(r"```yaml\s*(.*?)\s*```", response_text, re.DOTALL)
        if not yaml_match:
            # Try without code fences
            yaml_match = re.search(r"passed:\s*(true|false)\s*reason:\s*\|?\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
            if yaml_match:
                passed_str = yaml_match.group(1).strip().lower()
                reason = yaml_match.group(2).strip() if len(yaml_match.groups()) > 1 else ""
                return {
                    "passed": passed_str == "true",
                    "reason": reason
                }
            else:
                # Fallback: try to parse as YAML directly
                try:
                    result = yaml.safe_load(response_text)
                    if isinstance(result, dict) and "passed" in result:
                        return {
                            "passed": bool(result["passed"]),
                            "reason": str(result.get("reason", "No reason provided"))
                        }
                except:
                    pass
        
        if yaml_match:
            yaml_content = yaml_match.group(1).strip()
            result = yaml.safe_load(yaml_content)
            
            if isinstance(result, dict) and "passed" in result:
                return {
                    "passed": bool(result["passed"]),
                    "reason": str(result.get("reason", "No reason provided")).strip()
                }
        
        # If parsing failed, return error
        return {
            "passed": False,
            "reason": f"Failed to parse evaluation response: {response_text[:200]}"
        }
        
    except Exception as e:
        return {
            "passed": False,
            "reason": f"Error during evaluation: {str(e)}"
        }


def main():
    """Main function to evaluate benchmark results."""
    # Find latest benchmark file
    benchmark_file = find_latest_benchmark_file()
    
    if not benchmark_file:
        print("No benchmark file found. Please run the workflow agent first.")
        return
    
    print(f"Reading benchmark file: {benchmark_file}")
    
    # Load benchmark entries
    with open(benchmark_file, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    
    print(f"Found {len(entries)} entries to evaluate\n")
    
    # Evaluate each entry
    results = []
    passed_count = 0
    failed_count = 0
    
    for i, entry in enumerate(entries, 1):
        entry_id = entry.get('id', i)
        print(f"[{i}/{len(entries)}] Evaluating entry {entry_id}...")
        
        input_text = entry.get('input', '')
        instruction = entry.get('instruction', '')
        agent_output = entry.get('agent_answer', '')
        expected_answer = entry.get('expected_answer', '')
        
        if not agent_output:
            print(f"  ⚠️  No agent_answer found, skipping...")
            passed = False
            reason = "No agent_answer found in entry"
        else:
            # Evaluate
            evaluation = evaluate_agent_output(
                input_text=input_text,
                instruction=instruction,
                agent_output=agent_output,
                expected_answer=expected_answer
            )
            passed = evaluation["passed"]
            reason = evaluation["reason"]
        
        # Add passed and reason directly to entry
        entry["passed"] = passed
        entry["reason"] = reason
        
        if passed:
            passed_count += 1
            print(f"  ✅ PASSED: {reason[:100]}...")
        else:
            failed_count += 1
            print(f"  ❌ FAILED: {reason[:100]}...")
        
        results.append(entry)
        print()
    
    # Save results back to the original benchmark file
    with open(benchmark_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("=" * 60)
    print("Evaluation Summary")
    print("=" * 60)
    print(f"Total entries: {len(entries)}")
    print(f"Passed: {passed_count} ({passed_count/len(entries)*100:.1f}%)")
    print(f"Failed: {failed_count} ({failed_count/len(entries)*100:.1f}%)")
    print(f"\nResults saved to: {benchmark_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()

