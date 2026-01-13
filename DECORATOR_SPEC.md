Absolutely. Below is a v1 product spec you can hand directly to a coding agent or include as a formal design artifact. It’s written to be explicit, opinionated, and evolvable, and it incorporates everything we’ve discussed: enums, decorators, async/streaming, FastAPI safety, semantic → OTEL mapping, adapters, and invariants.

⸻

LLM Ops SDK — Decorator-Based Telemetry API (v1 Product Spec)

1. Overview

This SDK provides a stable, backend-agnostic telemetry interface for LLM- and agent-based applications.
Version 1 focuses on:
	•	A decorator-based API for instrumenting functions
	•	A typed semantic vocabulary (Enums) for correctness and discoverability
	•	Clean support for FastAPI, async, and streaming (generators)
	•	Centralized mapping from developer semantics → OTEL GenAI
	•	Adapter-based backends (OTLP, MLflow, Arize, etc.)

The core design goal is to allow teams to change telemetry backends without changing application code, while ensuring telemetry never interferes with business logic.

⸻

2. Design Goals and Non-Goals

2.1 Goals
	•	Provide a stable, explicit semantic interface for LLM Ops telemetry
	•	Support modern Python applications:
	•	FastAPI
	•	async / await
	•	streaming responses (sync + async generators)
	•	Ensure correctness by construction using typed semantics
	•	Centralize all OTEL GenAI and backend-specific logic
	•	Fail open: telemetry must never break production workloads

2.2 Non-Goals
	•	Automatic inference of prompts, models, or agent structure
	•	Encoding backend-specific concepts in user-facing APIs
	•	Deep inspection of function arguments or control flow
	•	Modeling agent workflows implicitly via decorators

⸻

3. Core Abstractions

3.1 Semantic Span

A Semantic Span represents a developer-declared unit of meaning in an LLM system, such as:
	•	an agent run
	•	a planning step
	•	a tool call
	•	an LLM generation

Semantic spans are backend-agnostic and OTEL-agnostic.

⸻

3.2 Semantic Kind Enum (v1)

Version 1 uses a typed enum instead of free-form strings to ensure correctness.

from enum import Enum

class SemanticKind(Enum):
    AGENT_RUN = "agent.run"
    AGENT_PLAN = "agent.plan"
    AGENT_STEP = "agent.step"
    TOOL_CALL = "tool.call"
    RETRIEVE = "retrieve"
    LLM_GENERATE = "llm.generate"
    LLM_EMBED = "llm.embed"

Rationale
	•	Prevents typos and semantic drift
	•	Enables IDE autocomplete and discoverability
	•	Allows early validation at import time
	•	Establishes a stable contract for semantic → OTEL mapping

Strings may be supported as an escape hatch in later versions but are not the primary API in v1.

⸻

4. Decorator API

4.1 Primary Decorator Factory

llmops.semantic(
    kind: SemanticKind,
    *,
    name: str | None = None
)

Responsibilities
	•	Declare a semantic boundary
	•	Start and end a semantic span around the function invocation
	•	Preserve function signature and execution semantics

Non-Responsibilities
	•	Extracting prompts, models, or tokens
	•	Inferring agent behavior
	•	Performing OTEL or backend logic directly

⸻

4.2 Usage Examples

Sync Function

@llmops.semantic(SemanticKind.AGENT_PLAN)
def plan(state: AgentState) -> Plan:
    ...

Async Function

@llmops.semantic(SemanticKind.TOOL_CALL, name="search")
async def search(query: str) -> SearchResult:
    ...

FastAPI Route

@app.post("/chat")
@llmops.semantic(SemanticKind.AGENT_RUN)
async def chat(req: ChatRequest):
    ...


⸻

5. Async and Streaming Support

The decorator must correctly handle all callable types:

Callable Type	Behavior
Sync function	Span wraps function call
Async function	Span wraps awaited execution
Generator	Span lives for generator lifetime
Async generator	Span lives for async generator lifetime

Streaming Example (Async Generator)

@llmops.semantic(SemanticKind.LLM_GENERATE)
async def generate(prompt: str):
    llmops.emit_input(prompt)
    llmops.emit_model("gpt-4.1")

    async for token in client.stream(prompt):
        llmops.emit_token(token)
        yield token

Span Lifecycle
	•	Starts on first iteration
	•	Ends on exhaustion, cancellation, or error

⸻

6. Semantic Enrichment (Inside Functions)

Decorators define structure, not meaning.

Meaning is supplied explicitly via SDK calls:

llmops.emit_input(prompt)
llmops.emit_model(model="gpt-4.1")
llmops.emit_tokens(input=123, output=456)

Key Properties
	•	Attach to the current semantic span
	•	No-op safely if no span exists
	•	Do not require OTEL knowledge

⸻

7. FastAPI Compatibility

Requirements
	•	Decorators must preserve:
	•	function signature
	•	annotations
	•	dependency injection behavior

Implementation Constraints
	•	functools.wraps is mandatory
	•	No argument reordering or mutation
	•	No dependency on request context internals

This ensures seamless compatibility with FastAPI routing, validation, and DI.

⸻

8. Semantic Validation

8.1 Import-Time Validation
	•	Decorator validates that kind is a known SemanticKind
	•	Validation happens when the module is loaded

8.2 Validation Modes

Mode	Behavior
Strict (dev / CI)	Unknown kind → error
Permissive (prod)	Unknown kind → warning + custom.*

8.3 Runtime Warnings (Non-Fatal)

Examples:
	•	LLM_GENERATE span with no emit_model
	•	TOOL_CALL without a name
	•	AGENT_RUN with no child spans

Warnings are advisory and never break execution.

⸻

9. Semantic → OTEL GenAI Mapping

All mappings are centralized and versioned.

Example:

SemanticKind.LLM_GENERATE
↓
OTEL Span:
  span.kind = INTERNAL
  attributes:
    gen_ai.operation = "generate"

emit_input(prompt)
↓
OTEL Event:
  name = "gen_ai.prompt"

Properties
	•	Deterministic
	•	Testable
	•	Invisible to users
	•	Independent of backend adapters

⸻

10. Backend Adapters

Adapters translate OTEL data into backend-specific representations.

Supported backends (initial):
	•	Raw OTLP
	•	MLflow
	•	Arize

Adapter Invariants
	•	No adapter logic leaks into user code
	•	Backend changes require no application changes
	•	Adapters may be swapped at runtime via configuration

⸻

11. Failure and Safety Guarantees

Hard Invariants
	•	Telemetry must never:
	•	change return values
	•	swallow exceptions
	•	alter control flow
	•	block execution

Error Handling
	•	All telemetry failures are caught and logged
	•	SDK fails open by default
	•	Optional strict mode for testing environments

⸻

12. Extensibility Roadmap (Post-v1)

Planned extensions:
	•	Purpose-built decorators:

@llmops.agent.plan
@llmops.tool.call("search")
@llmops.llm.generate


	•	Framework-specific presets (FastAPI, Google ADK)
	•	Linting rules and static analysis
	•	Expanded semantic taxonomy
	•	Cross-language parity

Enums remain the canonical internal representation even as ergonomics evolve.

⸻

13. Key Takeaways
	•	Decorators mark semantic boundaries, not logic
	•	Enums provide correctness, discoverability, and stability
	•	Async and streaming are first-class citizens
	•	FastAPI compatibility is a non-negotiable invariant
	•	Semantic → OTEL → backend mapping is centralized
	•	The SDK optimizes for boring, predictable, safe behavior


