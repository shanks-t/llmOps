# Phoenix/Arize Evaluators Reference

Working document covering Arize's evaluator features, APIs, and areas requiring further research.

## 1. Overview

The `arize-phoenix-evals` library provides LLM-as-a-judge evaluation capabilities:

- **Standalone package**: Works independently of main `arize-phoenix` package
- **Language support**: Python and TypeScript
- **Paradigm**: LLM-based evaluation with structured output
- **Integration**: Works with any LLM provider (OpenAI, Anthropic, Gemini, etc.)

### Installation

```bash
# Python
pip install arize-phoenix-evals

# TypeScript
npm install @arizeai/phoenix-evals
```

## 2. Evaluator Types

### 2.1 Pre-Built Evaluators

Phoenix provides battle-tested evaluators for common use cases:

| Evaluator | Purpose | Input Schema | Benchmark |
|-----------|---------|--------------|-----------|
| **Faithfulness** | Hallucination detection | input, output, context | HaluEval (93% precision GPT-4) |
| **RAG Relevance** | Retrieved chunk relevance | query, reference | MS Marco, WikiQA |
| **Q&A Correctness** | Answer correctness | query, response, context | WikiQA |
| **Summarization** | Summary quality | document, summary | GigaWorld, CNNDM, Xsum |
| **Toxicity** | Harmful content detection | text | WikiToxic |
| **Code Generation** | Code correctness | query, code | HumanEval, WikiSQL |
| **SQL Generation** | SQL query correctness | query, sql | WikiSQL |
| **Reference/Citation** | Citation validity | response, references | - |
| **User Frustration** | User sentiment | conversation | - |

#### Agent-Specific Evaluators

| Evaluator | Purpose | Description |
|-----------|---------|-------------|
| **Agent Function Calling** | Tool selection & params | Did agent call the right tool with correct parameters? |
| **Agent Path Convergence** | Goal efficiency | Did agent reach goal efficiently? |
| **Agent Planning** | Plan reasonableness | Is the agent's plan reasonable? |
| **Agent Reflection** | Self-correction | Does agent self-correct errors? |

### 2.2 Custom Evaluators

Two approaches for building custom evaluators:

#### ClassificationEvaluator (Recommended)

For categorical/classification tasks:

```python
from phoenix.evals import ClassificationEvaluator
from phoenix.evals.llm import LLM

TEMPLATE = """
Evaluate if the response answers the question correctly.

[Question]: {question}
[Response]: {response}

Respond with "correct" or "incorrect".
"""

evaluator = ClassificationEvaluator(
    name="qa_correctness",
    prompt_template=TEMPLATE,
    model=LLM(provider="openai", model="gpt-4o"),
    choices={"incorrect": 0, "correct": 1},
    direction="maximize"
)

result = evaluator.evaluate({
    "question": "What is 2+2?",
    "response": "4"
})
# Score(name='qa_correctness', score=1, label='correct', ...)
```

#### LLMEvaluator (Advanced)

For complex evaluation logic that doesn't fit classification:

```python
from phoenix.evals.evaluators import LLMEvaluator, EvalInput, Score
from typing import List

class CustomEvaluator(LLMEvaluator):
    PROMPT = """Your custom prompt template..."""
    
    TOOL_SCHEMA = {
        "type": "object",
        "properties": {
            "rating": {"type": "integer", "minimum": 1, "maximum": 10},
            "explanation": {"type": "string"}
        },
        "required": ["rating", "explanation"]
    }
    
    def __init__(self, llm: LLM):
        super().__init__(
            name="custom_eval",
            llm=llm,
            prompt_template=self.PROMPT,
            direction="maximize",
        )
    
    def _evaluate(self, eval_input: EvalInput) -> List[Score]:
        prompt_filled = self.prompt_template.render(variables=eval_input)
        response = self.llm.generate_object(
            prompt=prompt_filled,
            schema=self.TOOL_SCHEMA,
        )
        return [
            Score(
                score=response["rating"],
                name=self.name,
                explanation=response.get("explanation"),
                metadata={"model": self.llm.model},
                kind=self.kind,
                direction=self.direction,
            )
        ]
```

### 2.3 Code Evaluators (Non-LLM)

For deterministic evaluation logic:

```python
from phoenix.evals import CodeEvaluator

def check_json_valid(output: str) -> dict:
    """Check if output is valid JSON."""
    import json
    try:
        json.loads(output)
        return {"score": 1, "label": "valid"}
    except json.JSONDecodeError:
        return {"score": 0, "label": "invalid"}

json_evaluator = CodeEvaluator(
    name="json_validity",
    func=check_json_valid,
    direction="maximize"
)
```

## 3. API Reference

### 3.1 LLM Configuration

```python
from phoenix.evals.llm import LLM

# OpenAI
llm = LLM(provider="openai", model="gpt-4o")

# Anthropic
llm = LLM(provider="anthropic", model="claude-3-5-sonnet")

# Google
llm = LLM(provider="google", model="gemini-1.5-pro")

# Azure OpenAI
llm = LLM(
    provider="azure_openai",
    model="gpt-4",
    api_base="https://your-resource.openai.azure.com/",
    api_version="2024-02-15-preview"
)
```

### 3.2 Single Evaluation

```python
evaluator = ClassificationEvaluator(...)

# Synchronous
result = evaluator.evaluate({"input": "...", "output": "..."})

# Asynchronous
result = await evaluator.aevaluate({"input": "...", "output": "..."})
```

### 3.3 Batch Evaluation with llm_classify

For evaluating DataFrames efficiently:

```python
from phoenix.evals import llm_classify

results = llm_classify(
    dataframe=df,                    # pandas DataFrame
    template=TEMPLATE,               # prompt template string
    model=model,                     # LLM instance
    rails=["correct", "incorrect"],  # valid response labels
    provide_explanation=True,        # include reasoning
    concurrency=10,                  # parallel requests
)
# Returns DataFrame with 'label', 'score', 'explanation' columns
```

### 3.4 Integration with Phoenix Traces

Full workflow for evaluating traces:

```python
from phoenix.client import Client
from phoenix.evals import FaithfulnessEvaluator
from phoenix.evals.utils import to_annotation_dataframe

# 1. Initialize client
client = Client(endpoint="http://localhost:6006")

# 2. Export trace spans
df = client.spans.get_spans_dataframe(
    project_identifier="genai-service",
    filter="openinference.span.kind == 'AGENT'"
)

# 3. Prepare evaluation data
eval_df = df[["input.value", "output.value", "context"]].rename(columns={
    "input.value": "input",
    "output.value": "output"
})

# 4. Run evaluation
evaluator = FaithfulnessEvaluator(llm=LLM(provider="openai", model="gpt-4o"))
results = evaluator.evaluate_dataframe(eval_df)

# 5. Log annotations back to Phoenix
annotations = to_annotation_dataframe(results, span_ids=df["span_id"])
client.spans.log_span_annotations_dataframe(dataframe=annotations)
```

### 3.5 AX-Integrated Evaluations (Span, Trace, Session)

AX uses the same Phoenix evals primitives under the hood, but spans/traces/sessions are exported from AX and results are logged back as evaluation annotations. Templates are LLM-as-judge prompt definitions with variables mapped to span/trace/session attributes.

#### 3.5.1 One Flow for Hallucination, Omission, Redundancy

This flow stays AX-native: export telemetry, run LLM-based evaluators, log the results back to AX.

```python
from arize.exporter import ArizeExportClient
from arize.utils.types import Environments
from arize.pandas.logger import Client
from datetime import datetime, timedelta, timezone
import pandas as pd

from phoenix.evals import create_classifier, async_evaluate_dataframe
from phoenix.evals.llm import LLM
from phoenix.evals.utils import to_annotation_dataframe

export_client = ArizeExportClient(api_key="ARIZE_API_KEY")
logger = Client()

spans_df = export_client.export_model_to_df(
    space_id="ARIZE_SPACE_ID",
    model_id="YOUR_MODEL_ID",
    environment=Environments.TRACING,
    start_time=datetime.now(timezone.utc) - timedelta(days=7),
    end_time=datetime.now(timezone.utc),
)

# Prepare inputs (span-level). Adjust attribute paths to match your schema.
eval_df = spans_df[[
    "attributes.input.value",
    "attributes.output.value",
    "attributes.context",
    "context.span_id",
]].rename(columns={
    "attributes.input.value": "input",
    "attributes.output.value": "output",
    "attributes.context": "context",
    "context.span_id": "span_id",
})

llm = LLM(provider="openai", model="gpt-4o-mini")

HALLUCINATION_PROMPT = """
You are evaluating if the model answer is grounded in the provided context.

[Question]: {input}
[Answer]: {output}
[Context]: {context}

Respond with "faithful" or "hallucinated".
"""

OMISSION_PROMPT = """
You are evaluating whether the answer omits required facts from the context.

[Question]: {input}
[Answer]: {output}
[Context]: {context}

Respond with "complete" or "omitted".
"""

REDUNDANCY_PROMPT = """
You are evaluating whether the answer is redundant.

[Answer]: {output}

Respond with "concise" or "redundant".
"""

hallucination_eval = create_classifier(
    name="hallucination",
    llm=llm,
    prompt_template=HALLUCINATION_PROMPT,
    choices={"hallucinated": 0.0, "faithful": 1.0},
)

omission_eval = create_classifier(
    name="omission",
    llm=llm,
    prompt_template=OMISSION_PROMPT,
    choices={"omitted": 0.0, "complete": 1.0},
)

redundancy_eval = create_classifier(
    name="redundancy",
    llm=llm,
    prompt_template=REDUNDANCY_PROMPT,
    choices={"redundant": 0.0, "concise": 1.0},
)

results_df = await async_evaluate_dataframe(
    dataframe=eval_df,
    evaluators=[hallucination_eval, omission_eval, redundancy_eval],
)

annotations_df = to_annotation_dataframe(results_df, span_ids=eval_df["span_id"])
logger.log_evaluations_sync(annotations_df, "your-project-name")
```

#### 3.5.2 Session-Level (Multi-Turn) Variant

Use session-level evaluations when omissions or redundancy show up across turns. The key difference is that inputs/outputs are concatenated across all spans in the session.

```python
def prepare_sessions(df: pd.DataFrame) -> pd.DataFrame:
    sessions = []
    grouped = df.sort_values("start_time").groupby(
        "attributes.session.id", as_index=False
    )
    for session_id, group in grouped:
        sessions.append(
            {
                "session_id": session_id,
                "user_inputs": group["attributes.input.value"].dropna().tolist(),
                "output_messages": group["attributes.output.value"].dropna().tolist(),
            }
        )
    return pd.DataFrame(sessions)

sessions_df = prepare_sessions(spans_df)

SESSION_OMISSION_PROMPT = """
You are evaluating a full conversation for missing required information.

[User Inputs]: {user_inputs}
[Assistant Outputs]: {output_messages}

Respond with "complete" or "omitted".
"""

session_omission_eval = create_classifier(
    name="session_omission",
    llm=llm,
    prompt_template=SESSION_OMISSION_PROMPT,
    choices={"omitted": 0.0, "complete": 1.0},
)

session_results = await async_evaluate_dataframe(
    dataframe=sessions_df,
    evaluators=[session_omission_eval],
)

# Log session-level evals to the root span of the first trace in each session.
root_spans = spans_df[spans_df["parent_id"].isna()][
    ["attributes.session.id", "context.span_id"]
]
results_with_spans = pd.merge(
    session_results.reset_index(),
    root_spans,
    left_on="session_id",
    right_on="attributes.session.id",
    how="left",
).set_index("context.span_id", drop=False)

session_annotations = to_annotation_dataframe(results_with_spans)
logger.log_evaluations_sync(session_annotations, "your-project-name")
```

### 3.6 SDK-First Custom Code Evals (No UI)

Custom code evaluators in AX are UI-only today. The SDK-first workaround is to run your Python logic locally against exported AX telemetry, then log the results as annotations. This preserves an API-first flow and avoids UI setup.

#### 3.6.1 Example: Redundancy via Code (Local)

```python
from typing import Dict
import re

def redundancy_score(output: str) -> Dict[str, str | float]:
    sentences = [s.strip() for s in re.split(r"[.!?]", output) if s.strip()]
    unique = set(sentences)
    if not sentences:
        return {"label": "concise", "score": 1.0}
    ratio = len(unique) / len(sentences)
    label = "redundant" if ratio < 0.8 else "concise"
    score = 0.0 if label == "redundant" else 1.0
    return {"label": label, "score": score}

results = []
for _, row in eval_df.iterrows():
    result = redundancy_score(row["output"])
    results.append(
        {
            "span_id": row["span_id"],
            "label": result["label"],
            "score": result["score"],
            "explanation": "Sentence repetition ratio below threshold",
            "name": "redundancy_code",
        }
    )

results_df = pd.DataFrame(results).set_index("span_id", drop=False)
annotations_df = to_annotation_dataframe(results_df)
logger.log_evaluations_sync(annotations_df, "your-project-name")
```

#### 3.6.2 Example: Omission via Code (Local)

```python
REQUIRED_TERMS = {"pricing", "support", "limits"}

def omission_score(output: str) -> Dict[str, str | float]:
    present = {term for term in REQUIRED_TERMS if term in output.lower()}
    label = "omitted" if present != REQUIRED_TERMS else "complete"
    score = 0.0 if label == "omitted" else 1.0
    missing = sorted(REQUIRED_TERMS - present)
    explanation = "Missing: " + ", ".join(missing) if missing else "All present"
    return {"label": label, "score": score, "explanation": explanation}

results = []
for _, row in eval_df.iterrows():
    result = omission_score(row["output"])
    results.append(
        {
            "span_id": row["span_id"],
            "label": result["label"],
            "score": result["score"],
            "explanation": result["explanation"],
            "name": "omission_code",
        }
    )

results_df = pd.DataFrame(results).set_index("span_id", drop=False)
annotations_df = to_annotation_dataframe(results_df)
logger.log_evaluations_sync(annotations_df, "your-project-name")
```

### 3.7 Built-In vs Custom (No Code) vs SDK-First Code

| Approach | Best For | Custom Logic | Where It Runs | UI Required | Notes |
|----------|----------|--------------|---------------|-------------|-------|
| Built-in evals (LLM-as-judge) | Hallucination, basic omission, basic redundancy | Prompt-level | Your infra (eval calls) | No | Fastest onboarding, template-only |
| Custom LLM templates | Omission/rules in prompt | Prompt-level | Your infra (eval calls) | No | No code, but logic is still prompt-bound |
| SDK-first code evals | Deterministic omission/redundancy | Python logic | Local/offline, then log | No | Best when you want deterministic checks |

## 4. Pre-Built Evaluator Details

### 4.1 FaithfulnessEvaluator

Detects if LLM output is grounded in provided context (hallucination detection).

```python
from phoenix.evals import FaithfulnessEvaluator

evaluator = FaithfulnessEvaluator(
    llm=LLM(provider="openai", model="gpt-4o")
)

result = evaluator.evaluate({
    "input": "Where is the Eiffel Tower?",
    "output": "The Eiffel Tower is in Paris, France.",
    "context": "The Eiffel Tower is located in Paris."
})
# Score(label="faithful", score=1.0, ...)
```

**Note**: Designed for private/retrieved data, not general fact-checking.

### 4.2 Agent Function Calling Eval

Evaluates tool selection and parameter extraction:

```python
from phoenix.evals import (
    TOOL_CALLING_PROMPT_TEMPLATE,
    TOOL_CALLING_PROMPT_RAILS_MAP,
    llm_classify,
)

# DataFrame must have columns: question, tool_call, tool_definitions
results = llm_classify(
    dataframe=df,
    template=TOOL_CALLING_PROMPT_TEMPLATE,
    model=model,
    rails=list(TOOL_CALLING_PROMPT_RAILS_MAP.values()),
    provide_explanation=True
)
```

**Evaluates**:
- Was the correct tool selected?
- Were parameters correctly extracted from the query?
- Is the tool call syntactically correct/runnable?

### 4.3 RAG Relevance Eval

Evaluates if retrieved chunks are relevant to the query:

```python
from phoenix.evals import (
    RAG_RELEVANCY_PROMPT_TEMPLATE,
    RAG_RELEVANCY_PROMPT_RAILS_MAP,
    llm_classify,
)

results = llm_classify(
    dataframe=df,  # columns: query, reference
    template=RAG_RELEVANCY_PROMPT_TEMPLATE,
    model=model,
    rails=list(RAG_RELEVANCY_PROMPT_RAILS_MAP.values()),
)
```

## 5. Executor & Performance

### 5.1 Concurrency

Built-in parallel execution for batch evaluations:

```python
results = llm_classify(
    dataframe=df,
    template=TEMPLATE,
    model=model,
    rails=rails,
    concurrency=20,  # Up to 20 parallel requests
)
```

**Performance**: Up to 20x speedup compared to sequential API calls.

### 5.2 Batching

For large datasets, use batching to manage memory:

```python
from phoenix.evals import evaluate_dataframe

results = evaluate_dataframe(
    dataframe=large_df,
    evaluators=[evaluator1, evaluator2],
    batch_size=100,
)
```

## 6. Evaluator Tracing

Evaluators are natively instrumented with OpenTelemetry:

```python
# Enable evaluator tracing
import phoenix as px
px.launch_app()

# Evaluator calls will appear in Phoenix traces
results = evaluator.evaluate(eval_input)
```

This allows you to:
- Debug evaluator prompts
- Analyze evaluator latency
- Curate evaluator examples for improvement

## 7. Phoenix OSS vs Arize AX

### Confirmed Feature Parity

| Feature | Phoenix (OSS) | Arize AX |
|---------|---------------|----------|
| Pre-built evaluators | Yes | Yes |
| Custom evaluators | Yes | Yes |
| ClassificationEvaluator | Yes | Yes |
| LLMEvaluator base class | Yes | Yes |
| Code evaluators | Yes | Yes |
| Batch evaluation (llm_classify) | Yes | Yes |
| Concurrent execution | Yes | Yes |
| Evaluator tracing | Yes | Yes |
| Log annotations to traces | Yes | Yes |

### Research Needed: AX-Only Features

| Feature | Phoenix (OSS) | Arize AX | Status |
|---------|---------------|----------|--------|
| **Real-time guardrails** | Unknown | Claimed | Needs verification |
| **Online eval pipelines** | Unknown | Claimed | Needs verification |
| **Guardrails AI integration** | Unknown | Claimed | Needs verification |
| **Auto-scaling eval jobs** | No | Unknown | Needs verification |
| **Eval result dashboards** | Basic | Advanced? | Needs comparison |

### Questions to Research

1. **Real-time guardrails**: Can AX run evaluations inline (before response is returned to user) vs batch-only in Phoenix?

2. **Online pipelines**: Does AX support automatic evaluation triggers on new traces?

3. **Guardrails AI**: What's the integration depth? Is it just compatibility or native support?

4. **Enterprise features**: Rate limiting, audit logs, RBAC for eval configs?

## 8. Best Practices

### 8.1 Evaluator Selection

| Use Case | Recommended Evaluator |
|----------|----------------------|
| RAG hallucination | FaithfulnessEvaluator |
| Agent tool use | TOOL_CALLING_PROMPT_TEMPLATE |
| Retrieved chunk quality | RAG_RELEVANCY_PROMPT_TEMPLATE |
| Toxic/harmful content | Toxicity evaluator |
| Custom business logic | ClassificationEvaluator |
| Deterministic checks | CodeEvaluator |

### 8.2 Testing Custom Evaluators

```python
# 1. Create labeled ground truth
test_cases = [
    {"input": "...", "output": "...", "expected": "correct"},
    {"input": "...", "output": "...", "expected": "incorrect"},
]

# 2. Run evaluator
results = [evaluator.evaluate(tc) for tc in test_cases]

# 3. Calculate metrics
from sklearn.metrics import precision_score, recall_score, f1_score

y_true = [tc["expected"] for tc in test_cases]
y_pred = [r.label for r in results]

print(f"Precision: {precision_score(y_true, y_pred, pos_label='correct')}")
print(f"Recall: {recall_score(y_true, y_pred, pos_label='correct')}")
print(f"F1: {f1_score(y_true, y_pred, pos_label='correct')}")
```

### 8.3 Binary vs Numeric Ratings

**Recommendation**: Prefer binary/categorical labels over numeric ratings.

> LLMs have inherent limitations in numeric reasoning, and numeric scores correlate less well with human judgments.
> — [Arize Technical Report](https://arize.com/blog/testing-binary-vs-score-llm-evals-on-the-latest-models/)

```python
# PREFERRED: Binary classification
choices = {"incorrect": 0, "correct": 1}

# AVOID: Likert scale (unless necessary)
choices = {str(i): i for i in range(1, 11)}
```

## 9. Open Questions

- [ ] Does Phoenix support real-time (inline) evaluation, or batch only?
- [ ] What AX-only guardrail features exist?
- [ ] How do online evaluation pipelines work in AX?
- [ ] Pricing/limits differences for evals between Phoenix Cloud and AX?
- [ ] Can evaluators be versioned/managed like prompts?
- [ ] Is there a way to A/B test evaluator configurations?

## References

- [Phoenix Evaluation Docs](https://docs.arize.com/phoenix/evaluation)
- [Pre-Built Evaluators](https://docs.arize.com/phoenix/evaluation/running-pre-tested-evals)
- [Custom Evaluators Guide](https://docs.arize.com/phoenix/evaluation/how-to-evals/custom-llm-evaluators)
- [arize-phoenix-evals Python API](https://arize-phoenix.readthedocs.io/projects/evals/en/latest/)
- [Evaluation Benchmarks (GitHub)](https://github.com/Arize-ai/phoenix/tree/main/tutorials/evals)
