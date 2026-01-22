## Source of Truth

The **Product Requirements Document (PRD)** is the primary source of truth.

All design decisions, APIs, and implementations **must be traceable back to the PRD**.

If an implementation or design conflicts with the PRD:
- The PRD must be updated **first**, or
- The implementation must be revised

No silent divergence is allowed.

---

## Development Lifecycle (Feedback Loop)

This project follows a **progressive constraint model**, moving from intent → structure → mechanics, with continuous feedback.

### 1. Product Requirements (PRD)

**Defines truth.**

- What the system must do
- Non-goals
- Invariants (e.g. safety, extensibility, failure modes)
- Constraints (latency, observability, compatibility)

Agents must:
- Treat the PRD as authoritative
- Surface ambiguities or contradictions
- Propose PRD updates explicitly when gaps are found

---

### 2. Conceptual Architecture

**Aligns understanding.**

- High-level system shape
- Major components and responsibilities
- Data and control flow at a conceptual level

Characteristics:
- No concrete technologies
- No class-level detail
- Diagrams and plain language preferred

Purpose:
- Ensure all contributors share the same mental model
- Prevent premature implementation decisions

---

### 3. Reference Architecture

**Encodes architectural wisdom.**

Defines:
- Core architectural patterns
- Invariants that must hold across implementations
- Responsibility boundaries
- Extension points

Examples:
- Layering and separation of concerns
- Error-handling guarantees
- Async and streaming behavior rules
- Plugin or adapter models

Key rule:
> The reference architecture describes **how systems of this kind should be built**, not how one specific implementation works.

---

### 4. API Design

**Reviewed ruthlessly.**

API design is treated as a first-class artifact.

Includes:
- Public interfaces and contracts
- Types, enums, and expected semantics
- Default behavior and failure modes
- Examples and anti-examples

Principles:
- Make correct usage easy
- Make incorrect usage hard
- Optimize for clarity and long-term stability

If the API feels awkward in examples, the API is wrong.

---

### 5. Tests (Executable Contracts)

**Executable behavior defines correctness.**

Tests are the **first executable artifact** derived from the PRD and API specification. They serve as contracts that must be satisfied before any implementation is considered complete.

#### Core Philosophy

We adopt **BDD semantics using pytest primitives**:

- Tests are executable contracts
- Behavior lives in structure, naming, and docstrings
- pytest is the only required test dependency
- Traceability is enforced by layout and metadata
- Agents reason over tests as specs

Think of this as: **"Structured pytest as executable design."**

#### Directory Structure

```
llm-observability-sdk/tests/
├── prd_01/
│   ├── README.md                       # Coverage map for PRD_01
│   ├── test_init_spec.py               # Init capability
│   ├── test_validation_spec.py         # Validation modes
│   └── ...
├── prd_02/
│   └── ...
└── conftest.py                         # Shared fixtures
```

#### Traceability Mechanisms

**1. Directory-level binding (hard guarantee)**

```
tests/prd_01/
```

- Impossible to miss PRD association
- Impossible to mix PRDs accidentally
- Easy to delete/regenerate wholesale

**2. File-level binding (capability mapping)**

Each `tests/prd_XX/README.md` provides a navigation index:

```markdown
# PRD_01 — Behavioral Test Coverage

This directory contains executable contracts derived from:

- PRD: docs/prd/PRD_01.md
- API Spec: docs/api_spec/API_SPEC_01.md

## Coverage Map

| Capability | Test File | API Methods |
|------------|-----------|-------------|
| SDK initialization | test_init_spec.py | `init()` |
| Config validation | test_validation_spec.py | `init()` |
```

**3. Test file metadata (agent-readable)**

Each test file declares its scope:

```python
PRD_ID = "PRD_01"
API_SPEC_ID = "API_SPEC_01"
CAPABILITY = "init"
```

Agents can scan these constants to confirm scope and avoid leaking logic across PRDs.

**4. Test function naming (scenario as name)**

```python
def test_init_fails_without_config_in_strict_mode():
```

Names communicate intent, not mechanics.

**5. Docstrings (GIVEN/WHEN/THEN + metadata)**

```python
def test_instrument_resolves_config_from_env_var():
    """
    PRD: PRD_01
    API: API_SPEC_01.instrument()

    GIVEN a valid config file exists
    AND the LLMOPS_CONFIG_PATH environment variable is set to that path
    WHEN llmops.instrument() is called without arguments
    THEN a TracerProvider is returned
    """
```

This is machine-readable by agents and humans.

#### Coverage Requirements

- Every public API capability **must** have at least one contract test file
- Test files **must** be traceable to both a PRD and an API spec
- Test directories are versioned by PRD (naming: `prd_XX/`)
- Implementations **must** satisfy all contract tests before merging

#### Pre-Implementation Tests

Tests written before implementation use `xfail`:

```python
pytestmark = pytest.mark.xfail(reason="PRD_01 implementation pending", strict=False)
```

- Tests run and validate structure (imports, fixtures)
- Failures are expected and labeled `XFAIL`
- When implementation lands, tests show `XPASS`
- Remove the marker once implementation is complete

#### Principles

- Tests validate the contract **before** implementation
- Tests remain readable by non-authors
- Contract coverage reflects requirements in the PRD
- Test scenarios describe **what** must happen, not **how**

---

### Executable Contracts as Design Artifacts

Contract tests are treated as **design-level artifacts**, not test helpers.

#### Role in the System

Contract tests serve as:
- The **executable form** of the API contract
- The **primary input** for agentic implementation
- A **stability layer** across refactors and regenerations

> If code is deleted, regenerated, or refactored — **behavior survives**.

#### One-Way Dependency

```
PRD → API Spec → Tests → Code
```

Tests define behavior. Code satisfies tests. Not the reverse.

#### Agent Responsibilities

Agents must:
- Use tests under `tests/prd_XX/` as the source of behavioral truth
- Generate implementations that satisfy contract tests
- Flag ambiguous or underspecified behavior in tests
- Propose PRD or API spec changes when behavior intent is unclear
- Treat passing tests as the definition of "done"
- **Not change tests** unless the PRD or API spec is updated

**Recommended agent prompt:**

```
You are implementing functionality for PRD_01.
Use the tests under llm-observability-sdk/tests/prd_01/ as the source of behavioral truth.
Do not change tests unless the PRD or API spec is updated.
```

#### Human Responsibilities

Humans must:
- Keep test names precise and domain-aligned
- Avoid encoding implementation details in tests
- Update tests when requirements change (before updating code)
- Review contract tests as critically as API designs

#### Lifecycle

```
PRD change → API spec update → Contract test update → Implementation change
```

Contract tests must be updated **before** implementation changes when requirements evolve. This ensures:
- Behavior intent is captured first
- Agents have stable inputs
- Regressions are caught immediately

---

### 6. Implementation

**Small, reversible steps.**

Implementation should:
- Follow the approved API and architecture
- Avoid over-engineering (this is a POC)
- Prefer composability over completeness

Guidelines:
- Ship incrementally
- Favor refactors over rewrites
- Keep changes easy to revert

---

### 6. Continuous Feedback

At any stage, discoveries may trigger:
- PRD clarification
- Architecture refinement
- API adjustments

This loop is intentional and healthy.

**Docs and examples must evolve alongside code.**

---

## Package Management & Tooling

- **UV** is the required Python package manager
- Dependency definitions must be explicit and minimal
- Lockfiles must be kept up to date
- Avoid introducing tooling that complicates the POC unnecessarily

---

## Agent Operating Principles

Agents contributing to this repo must:

- Respect document hierarchy (PRD → architecture → API → code)
- Ask for clarification when requirements are ambiguous
- Propose changes explicitly rather than implicitly
- Keep solutions simple unless complexity is justified
- Prefer explanation and traceability over cleverness

---

## Optimization Priorities

This project optimizes for:

- **Clarity over cleverness**
- **Extensibility over completeness**
- **Invariants over features**

Performance, scale, and production hardening are **explicitly secondary** unless stated otherwise in the PRD.

---

## Non-Goals (for the POC)

- Full production readiness
- Perfect abstraction coverage
- Exhaustive feature sets
- Premature optimization

---

## Final Note

This repository is intended to model **how excellent API teams actually work**:

- Intent before implementation
- Architecture before mechanics
- APIs before code
- Documentation as a living artifact

If a choice must be made, always favor:
> Long-term understanding over short-term progress.
