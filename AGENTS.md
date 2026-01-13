# AGENTS.md

## Purpose

This repository is a **proof of concept (POC)** for a larger, production-grade system.  
The goal is to validate **architecture, APIs, and developer experience**, not to prematurely optimize or fully harden the system.

This document defines **how humans and coding agents collaborate** when designing, implementing, and iterating on this project.

---

## Source of Truth

The **Product Requirements Document (PRD)** is the primary source of truth.

All design decisions, APIs, and implementations **must be traceable back to the PRD**.

If an implementation or design conflicts with the PRD:
- The PRD must be updated **first**, or
- The implementation must be revised

No silent divergence is allowed.

---

## Project Structure

- `./docs/`
  - Contains the PRD, conceptual architecture, reference architecture, and API design documents
- INFRA.md`
  - Contains infrastructure-specific details (deployment, environments, cloud resources, etc.)
  - Treated as authoritative for infra concerns
- `./llm-observability-sdk/src`
  - Implementation code
- `examples/`
  - Canonical usage examples (must evolve alongside code)
- `./llm-observability-sdk/tests/`
  - Tests that enforce invariants and expected behavior

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

### 5. Implementation

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
