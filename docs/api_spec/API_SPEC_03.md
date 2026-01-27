# PRD_03 — API Specification

**Version:** 0.2
**Date:** 2026-01-27
**Status:** Draft
**Implements:** PRD_03

---

## 1. Overview

This document defines the public API for PRD_03: LLM-as-a-Judge Evaluator Templates. The SDK provides platform-agnostic evaluation capabilities through the `llmops.eval` namespace, enabling users to create, register, and use LLM-based evaluators.

**Design Principles:**
- Evaluation is accessed via the reserved `llmops.eval` namespace (per Design Philosophy)
- Evaluation is independent of telemetry (no `init()` required)
- LLM configuration is user-provided (SDK does not manage API keys)
- Built-in templates wrap `phoenix.evals` for consistency with Arize ecosystem

---

## 2. Package Structure

```
llmops/
├── __init__.py              # Re-exports eval namespace
├── eval/                    # NEW: Evaluation module
│   ├── __init__.py          # Public API: faithfulness, create_classifier, etc.
│   ├── _registry.py         # In-memory evaluator registry
│   └── templates/
│       ├── __init__.py
│       └── faithfulness.py  # Built-in Faithfulness template
└── ...                      # Other modules unchanged
```

---

## 3. Public API

### 3.1 Module Access

The evaluation module is accessed via the `llmops.eval` namespace.

**Access Pattern:**
```python
import llmops

# Access eval module (lazy-loaded)
evaluator = llmops.eval.faithfulness(llm=llm)
```

**Alternate Import:**
```python
from llmops import eval

evaluator = eval.faithfulness(llm=llm)
```

**Module-Level Access:**
```python
import llmops.eval

evaluator = llmops.eval.faithfulness(llm=llm)
```

---

### 3.2 `llmops.eval.faithfulness()`

Create a Faithfulness evaluator for hallucination detection.

**Signature:**
```python
def faithfulness(
    llm: "LLM",
) -> "FaithfulnessEvaluator":
    """
    Create a Faithfulness evaluator for detecting hallucinations.

    The Faithfulness evaluator checks whether an LLM's output is grounded
    in the provided context. It uses Phoenix Evals' benchmarked prompt
    template which achieves 93% precision on the HaluEval dataset.

    Args:
        llm: A phoenix.evals.llm.LLM instance configured with your
             preferred provider and model.

    Returns:
        A configured FaithfulnessEvaluator instance.

    Raises:
        ImportError: If arize-phoenix-evals is not installed.

    Example:
        >>> from phoenix.evals.llm import LLM
        >>> import llmops
        >>>
        >>> llm = LLM(provider="openai", model="gpt-4o")
        >>> evaluator = llmops.eval.faithfulness(llm=llm)
        >>>
        >>> scores = evaluator.evaluate({
        ...     "input": "What is the capital of France?",
        ...     "output": "Paris is the capital of France.",
        ...     "context": "Paris is the capital and largest city of France."
        ... })
        >>>
        >>> print(scores[0].label)  # "faithful" or "unfaithful"
        >>> print(scores[0].score)  # 1.0 or 0.0
    """
```

**Input Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `input` | `str` | Yes | The query or question |
| `output` | `str` | Yes | The LLM's response to evaluate |
| `context` | `str` | Yes | The reference context/documents |

**Output:**

Returns `list[Score]` with a single `Score` object:

| Field | Type | Values |
|-------|------|--------|
| `name` | `str` | `"faithfulness"` |
| `label` | `str` | `"faithful"` or `"unfaithful"` |
| `score` | `float` | `1.0` (faithful) or `0.0` (unfaithful) |
| `explanation` | `str` | LLM's reasoning for the judgment |
| `kind` | `str` | `"llm"` |
| `direction` | `str` | `"maximize"` |

---

### 3.3 `llmops.eval.create_classifier()`

Create a custom LLM-as-a-judge classification evaluator.

**Signature:**
```python
def create_classifier(
    name: str,
    prompt_template: str,
    llm: "LLM",
    choices: dict[str, float] | list[str],
    direction: str = "maximize",
) -> "ClassificationEvaluator":
    """
    Create a custom classification evaluator.

    This factory function wraps phoenix.evals.create_classifier to provide
    a convenient way to create LLM-as-a-judge evaluators for custom
    classification tasks.

    Args:
        name: Identifier for the evaluator. Used in Score objects and
              registry storage.
        prompt_template: Prompt with {placeholder} variables that will
                        be filled from the evaluation input dict.
        llm: A phoenix.evals.llm.LLM instance configured with your
             preferred provider and model.
        choices: Classification labels. Can be:
                 - list[str]: Labels only (scores will be None)
                 - dict[str, float]: Labels mapped to numeric scores
        direction: Score optimization direction.
                  "maximize" (default) = higher is better
                  "minimize" = lower is better

    Returns:
        A configured ClassificationEvaluator instance.

    Raises:
        ImportError: If arize-phoenix-evals is not installed.
        ValueError: If choices is empty.

    Example (binary classification with scores):
        >>> from phoenix.evals.llm import LLM
        >>> import llmops
        >>>
        >>> llm = LLM(provider="openai", model="gpt-4o")
        >>> tone_eval = llmops.eval.create_classifier(
        ...     name="tone_check",
        ...     prompt_template="Is this response professional? Response: {output}",
        ...     llm=llm,
        ...     choices={"professional": 1.0, "unprofessional": 0.0},
        ... )
        >>>
        >>> scores = tone_eval.evaluate({"output": "Hello, how can I help?"})
        >>> print(scores[0].label)  # "professional"
        >>> print(scores[0].score)  # 1.0

    Example (multi-class without scores):
        >>> sentiment_eval = llmops.eval.create_classifier(
        ...     name="sentiment",
        ...     prompt_template="Classify the sentiment: {text}",
        ...     llm=llm,
        ...     choices=["positive", "negative", "neutral"],
        ... )
        >>>
        >>> scores = sentiment_eval.evaluate({"text": "I love this!"})
        >>> print(scores[0].label)  # "positive"
        >>> print(scores[0].score)  # None
    """
```

**Prompt Template Variables:**

Variables in `{curly_braces}` are replaced with values from the evaluation input dict:

```python
prompt_template = """
Evaluate the response quality.

Question: {question}
Response: {response}
Context: {context}

Is the response accurate?
"""

# These variables must be provided in evaluate() input:
evaluator.evaluate({
    "question": "What is 2+2?",
    "response": "4",
    "context": "Basic arithmetic"
})
```

---

### 3.4 `llmops.eval.register()`

Register an evaluator by name for later retrieval.

**Signature:**
```python
def register(
    name: str,
    evaluator: "Evaluator",
) -> None:
    """
    Register an evaluator by name for project-wide reuse.

    The registry is process-local and non-persistent. Evaluators must be
    re-registered on each process start.

    Args:
        name: Unique identifier for the evaluator.
        evaluator: Any evaluator instance (built-in or custom).

    Returns:
        None

    Note:
        If an evaluator with the same name already exists, it will be
        silently overwritten. Use list() to check existing registrations.

    Example:
        >>> import llmops
        >>> from phoenix.evals.llm import LLM
        >>>
        >>> llm = LLM(provider="openai", model="gpt-4o")
        >>> faithfulness = llmops.eval.faithfulness(llm=llm)
        >>>
        >>> # Register for later use
        >>> llmops.eval.register("hallucination_check", faithfulness)
        >>>
        >>> # Later, in another module...
        >>> eval_ref = llmops.eval.get("hallucination_check")
    """
```

---

### 3.5 `llmops.eval.get()`

Retrieve a registered evaluator by name.

**Signature:**
```python
def get(
    name: str,
) -> "Evaluator":
    """
    Retrieve a registered evaluator by name.

    Args:
        name: The name used when registering the evaluator.

    Returns:
        The registered evaluator instance.

    Raises:
        KeyError: If no evaluator is registered with the given name.

    Example:
        >>> import llmops
        >>>
        >>> # Assuming "tone_check" was registered earlier
        >>> evaluator = llmops.eval.get("tone_check")
        >>> scores = evaluator.evaluate({"output": "Hello!"})

    Example (handling missing registration):
        >>> try:
        ...     evaluator = llmops.eval.get("unknown")
        ... except KeyError as e:
        ...     print(f"Evaluator not found: {e}")
    """
```

---

### 3.6 `llmops.eval.list()`

List all registered evaluator names.

**Signature:**
```python
def list() -> list[str]:
    """
    List all registered evaluator names.

    Returns:
        A list of registered evaluator names. Order is not guaranteed.

    Example:
        >>> import llmops
        >>>
        >>> llmops.eval.register("eval_a", evaluator_a)
        >>> llmops.eval.register("eval_b", evaluator_b)
        >>>
        >>> print(llmops.eval.list())
        ['eval_a', 'eval_b']
    """
```

---

### 3.7 `llmops.eval.clear()`

Clear all registered evaluators.

**Signature:**
```python
def clear() -> None:
    """
    Clear all registered evaluators.

    This is primarily intended for testing. In production, registered
    evaluators persist for the lifetime of the process.

    Returns:
        None

    Example:
        >>> import llmops
        >>>
        >>> llmops.eval.register("my_eval", evaluator)
        >>> print(llmops.eval.list())
        ['my_eval']
        >>>
        >>> llmops.eval.clear()
        >>> print(llmops.eval.list())
        []
    """
```

---

## 4. Types

### 4.1 Evaluator (Protocol)

Evaluators conform to the phoenix.evals Evaluator interface:

```python
from typing import Protocol

class Evaluator(Protocol):
    """Evaluator protocol for type checking."""

    @property
    def name(self) -> str:
        """Evaluator identifier."""
        ...

    def evaluate(
        self,
        eval_input: dict[str, Any],
        input_mapping: dict[str, str] | None = None,
    ) -> list["Score"]:
        """
        Evaluate a single input.

        Args:
            eval_input: Dictionary with required fields for this evaluator.
            input_mapping: Optional mapping from evaluator fields to input keys.

        Returns:
            List of Score objects (typically one).
        """
        ...

    async def async_evaluate(
        self,
        eval_input: dict[str, Any],
        input_mapping: dict[str, str] | None = None,
    ) -> list["Score"]:
        """Async variant of evaluate."""
        ...
```

### 4.2 Score

Evaluation results are returned as Score objects:

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class Score:
    """Evaluation result."""

    name: str | None = None
    """Evaluator name that produced this score."""

    score: float | None = None
    """Numeric score (if applicable)."""

    label: str | None = None
    """Classification label (if applicable)."""

    explanation: str | None = None
    """LLM's reasoning for the judgment."""

    metadata: dict[str, Any] | None = None
    """Additional metadata (e.g., model name)."""

    direction: str = "maximize"
    """Score optimization direction."""

    kind: str | None = None
    """Evaluator type: "llm", "code", or "human"."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        ...

    def pretty_print(self, indent: int = 2) -> None:
        """Print as formatted JSON."""
        ...
```

### 4.3 LLM

LLM instances are created using phoenix.evals:

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

**Note:** The SDK does not provide its own LLM wrapper. Users must create LLM instances using `phoenix.evals.llm.LLM` directly.

---

## 5. Error Handling

### 5.1 Missing Dependencies

When `arize-phoenix-evals` is not installed:

```python
>>> import llmops
>>> llmops.eval.faithfulness(llm=llm)
ImportError: Evaluation requires 'arize-phoenix-evals' package.
Install with: pip install llmops[eval]
```

**Key behaviors:**
- `import llmops` always succeeds
- `llmops.eval` triggers lazy load and dependency check
- Error message includes exact pip install command

### 5.2 Registry Errors

**Missing evaluator:**
```python
>>> llmops.eval.get("nonexistent")
KeyError: "Evaluator 'nonexistent' not registered"
```

**Empty choices:**
```python
>>> llmops.eval.create_classifier(
...     name="test",
...     prompt_template="...",
...     llm=llm,
...     choices=[]
... )
ValueError: choices cannot be empty
```

### 5.3 Evaluation Errors

Evaluation errors from the LLM are propagated to the caller:

```python
>>> evaluator.evaluate({"input": "...", "output": "...", "context": "..."})
# May raise if LLM API fails (rate limit, auth error, etc.)
```

**Note:** Unlike telemetry (which swallows errors), evaluation errors are propagated because they represent the primary operation the user requested.

---

## 6. Registry Behavior

### 6.1 Thread Safety

The registry uses a `threading.Lock` for all operations:

```python
import threading

_REGISTRY: dict[str, Evaluator] = {}
_LOCK = threading.Lock()

def register(name: str, evaluator: Evaluator) -> None:
    with _LOCK:
        _REGISTRY[name] = evaluator

def get(name: str) -> Evaluator:
    with _LOCK:
        if name not in _REGISTRY:
            raise KeyError(f"Evaluator '{name}' not registered")
        return _REGISTRY[name]
```

### 6.2 Lifecycle

| Event | Registry State |
|-------|----------------|
| Process start | Empty |
| After `register()` | Contains registered evaluators |
| After `clear()` | Empty |
| Process end | Contents lost |

### 6.3 Multi-Process Behavior

Each process has its own independent registry:

```python
# Worker 1
llmops.eval.register("my_eval", evaluator)

# Worker 2 (different process)
llmops.eval.get("my_eval")  # KeyError - not registered in this process
```

---

## 7. Installation

### 7.1 Optional Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
eval = [
    "arize-phoenix-evals>=2.0.0",
]
# Note: LLM provider SDKs (openai, anthropic, etc.) are user responsibility
```

### 7.2 Install Commands

```bash
# Evaluation support only
pip install llmops[eval]

# Both telemetry and evaluation
pip install llmops[arize,eval]

# Or install everything
pip install llmops[all]
```

---

## 8. Complete Examples

### 8.1 Basic Faithfulness Evaluation

```python
import llmops
from phoenix.evals.llm import LLM

# Create LLM instance (user responsibility)
llm = LLM(provider="openai", model="gpt-4o")

# Create evaluator
faithfulness = llmops.eval.faithfulness(llm=llm)

# Evaluate
scores = faithfulness.evaluate({
    "input": "What causes rain?",
    "output": "Rain is caused by water evaporating from oceans.",
    "context": "Rain occurs when water vapor condenses in clouds."
})

# Check result
score = scores[0]
print(f"Label: {score.label}")        # "faithful" or "unfaithful"
print(f"Score: {score.score}")        # 1.0 or 0.0
print(f"Explanation: {score.explanation}")
```

### 8.2 Custom Evaluator with Registry

```python
# setup.py or app startup
import llmops
from phoenix.evals.llm import LLM

def setup_evaluators():
    llm = LLM(provider="openai", model="gpt-4o-mini")

    # Create custom evaluator
    tone_eval = llmops.eval.create_classifier(
        name="professional_tone",
        prompt_template="""
        Evaluate if this customer service response is professional.

        Response: {response}

        A professional response is polite, clear, and helpful.
        An unprofessional response is rude, unclear, or dismissive.
        """,
        llm=llm,
        choices={"professional": 1.0, "unprofessional": 0.0},
    )

    # Register for project-wide use
    llmops.eval.register("tone", tone_eval)
    llmops.eval.register("hallucination", llmops.eval.faithfulness(llm))

# service.py
import llmops

def evaluate_response(response: str) -> dict:
    tone_eval = llmops.eval.get("tone")
    scores = tone_eval.evaluate({"response": response})
    return {
        "is_professional": scores[0].label == "professional",
        "explanation": scores[0].explanation,
    }
```

### 8.3 Evaluation Without Telemetry

Evaluation works independently of telemetry:

```python
import llmops
from phoenix.evals.llm import LLM

# No init() call needed!
# Evaluation is completely independent

llm = LLM(provider="openai", model="gpt-4o")
evaluator = llmops.eval.faithfulness(llm=llm)

scores = evaluator.evaluate({
    "input": "...",
    "output": "...",
    "context": "...",
})
```

### 8.4 Combined Telemetry and Evaluation

```python
import llmops
from phoenix.evals.llm import LLM

# Initialize telemetry (PRD_01)
llmops.init(config="llmops.yaml")

# Initialize evaluation (PRD_03) - independent of telemetry
llm = LLM(provider="openai", model="gpt-4o")
faithfulness = llmops.eval.faithfulness(llm=llm)

# Your app code...
# Traces go to configured backend
# Evaluations run locally with your LLM
```

---

## 9. Public API Summary

### Modules

| Module | Purpose |
|--------|---------|
| `llmops.eval` | Platform-agnostic evaluation API |

### Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `faithfulness` | `(llm: LLM)` | `FaithfulnessEvaluator` |
| `create_classifier` | `(name, prompt_template, llm, choices, direction?)` | `ClassificationEvaluator` |
| `register` | `(name: str, evaluator: Evaluator)` | `None` |
| `get` | `(name: str)` | `Evaluator` |
| `list` | `()` | `list[str]` |
| `clear` | `()` | `None` |

### Exceptions

| Exception | When Raised |
|-----------|-------------|
| `ImportError` | `arize-phoenix-evals` not installed |
| `KeyError` | Evaluator name not in registry |
| `ValueError` | Invalid arguments (e.g., empty choices) |

---

## 10. Anti-Patterns

### 10.1 Don't Store API Keys in Code

```python
# BAD - API key in code
llm = LLM(provider="openai", model="gpt-4o", api_key="sk-...")

# GOOD - Use environment variables
# Set OPENAI_API_KEY in environment
llm = LLM(provider="openai", model="gpt-4o")
```

### 10.2 Don't Assume Registry Persistence

```python
# BAD - Assuming registry survives restart
evaluator = llmops.eval.get("my_eval")  # KeyError after restart

# GOOD - Register at startup
def on_startup():
    llmops.eval.register("my_eval", create_my_evaluator())
```

### 10.3 Don't Mix Evaluation and Telemetry Dependencies

```python
# BAD - Assuming eval requires telemetry deps
llmops.init(...)  # Not needed for eval!

# GOOD - Eval works independently
llmops.eval.faithfulness(llm=llm)  # Just works
```

---

## 11. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/prd/PRD_03.md` | Requirements and success criteria |
| `docs/DESIGN_PHILOSOPHY.md` | Design principles and API stability rules |
| `docs/CONCEPTUAL_ARCHITECTURE.md` | High-level conceptual view |
| `docs/reference_architecture/REFERENCE_ARCHITECTURE_01.md` | Architectural patterns |
| `docs/api_spec/API_SPEC_01.md` | Telemetry API specification |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-27
