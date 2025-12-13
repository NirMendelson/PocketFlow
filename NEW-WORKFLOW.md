# Workflow Routing System (v1)

This document describes the deterministic, reliable routing of incoming user messages to the correct workflow. The LLM is used **only as a confidence scorer, not a decision maker**.

---

## Workflow Definition

Each workflow declares explicit routing signals:

```yaml
workflow: HandleAnnualPlanInquiry

keywords:
  - annual
  - yearly
  - subscription

examples:
  - "Do you have an annual plan?"
  - "Can I pay yearly?"
  - "Is there a subscription?"

steps:
  - id: provide_annual_plan_info
    action: reply
```

- **keywords**: used for fuzzy matching
- **examples**: used for semantic matching
- **steps**: workflow execution logic

---

## Routing Flow

### 1. Keyword Matching (no LLM)

- Fuzzy match user input against keywords.
- Exclude workflows with no keyword signal.

---

### 2. Semantic Matching on Examples

- Perform semantic search between user input and examples.
- Drop workflows below a relevance threshold.
- Result is a small candidate set (≈3–5 workflows).

---

### 3. Confidence Scoring (LLM)

- Pass remaining candidates to an LLM.
- LLM assigns a confidence score per workflow, e.g.:

  ```json
  { "workflow_id": "...", "confidence": 0.78 }
  ```

- The LLM does **not** choose a workflow; it simply scores candidates.

---

### 4. Selection Rules

Select the top workflow **only if**:
- `confidence >= 0.6`
- `top_confidence - second_confidence >= 0.2`

---

### 5. Fallback

If the selection rules fail:
- Trigger `ask_clarification_question`
- Do **not** execute any workflow

**Example clarification prompt:**  
> "Are you asking about our plans, or something else?"

---

## Principles

- Routing is classification, not generation.
- Keywords ensure recall; examples ensure meaning.
- LLMs validate; the system decides.
- When unsure, ask for clarification.

## Tasks

[x] add keywords to all workflows
[x] add examples to all workflows
[x] make semantic be on examples
[x] make fuzzy matching be on keywords
[] add logic of filter by low scores of semantic + fuzzy
[] update llm to get all relevant workflows and give confidence grade
[] add logic of filter by low confidence and fallback to ask_clarification_questions