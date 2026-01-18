# LLM Observability SDK

A unified auto-instrumentation SDK for LLM observability. Instrument your LLM applications with a single `init()` call and view traces in your preferred backend.

## Features

- **Auto-instrumentation**: Zero-code tracing for Google ADK, OpenAI, Anthropic, and more
- **Backend flexibility**: Switch between Phoenix (Arize) and MLflow via configuration
- **Privacy controls**: Opt-in content capture with sensible defaults
- **Async-native**: First-class support for async Python and streaming responses

## Prerequisites

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | >= 3.12 | Runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Package manager |
| [just](https://github.com/casey/just) | latest | Task runner |
| [Docker](https://www.docker.com/) | latest | Observability backends |
| `GOOGLE_API_KEY` | - | Required for examples and E2E tests |

### Install Prerequisites

```bash
# macOS
brew install just uv

# Or install just via cargo
cargo install just

# Install uv via pip
pip install uv
```

### Prek Hooks

This repo uses [prek](https://prek.j178.dev/) (a fast `pre-commit` replacement) to run local quality checks on every commit.

```bash
# Install prek (see https://prek.j178.dev/installation/ for options)
# Wire hooks into git
prek install

# Run hooks manually
prek run
```

## Installation

```bash
# From repository root
just install
```

All `just` commands work from the repository root - no need to `cd` into subdirectories.

## Quick Start

### 1. Start an observability backend

```bash
# Phoenix (recommended for LLM observability)
just start-phoenix

# Or MLflow
just start-mlflow

# Or both
just start-backends
```

### 2. Configure the SDK

Create `llmops.yaml` in your project root:

```yaml
service:
  name: "my-service"
  version: "1.0.0"

backend: phoenix  # or "mlflow"

phoenix:
  endpoint: http://localhost:6006/v1/traces

mlflow:
  tracking_uri: http://localhost:5001

privacy:
  capture_content: true  # Set false in production
```

### 3. Initialize in your code

```python
import llmops

llmops.init()  # Auto-instruments all supported libraries

# Your LLM calls are now automatically traced
response = openai.chat.completions.create(...)
```

### 4. Set your API key (for examples)

```bash
export GOOGLE_API_KEY=your-key-here
```

### 5. Run the example server

```bash
just run-example
```

### 6. View traces

- **Phoenix**: http://localhost:6006
- **MLflow**: http://localhost:5001

## Example Endpoints

The example server demonstrates five LLM workflow patterns:

```bash
# Simple chat
just chat message="What is the capital of France?"

# Multi-tool travel agent
just travel query="Plan a weekend trip to Tokyo"

# Code assistant
just code task="generate" prompt="Write a fibonacci function"

# Research workflow (RAG pattern)
just research topic="quantum computing"

# Streaming response
just stream prompt="Explain photosynthesis"
```

## Available Commands

Run `just --list` from the repository root to see all commands organized by group.

### Justfile Structure

This repository uses a **delegation pattern** with two Justfiles:

| File | Purpose |
|------|---------|
| `./Justfile` | Root entry point - delegates to SDK |
| `./llm-observability-sdk/Justfile` | SDK-specific recipes |

You can run commands from either location:

```bash
# From repo root (recommended)
just test
just lint

# Direct SDK access (equivalent)
just sdk test
cd llm-observability-sdk && just test
```

### Key Recipes

### Quality Checks

| Command | Description |
|---------|-------------|
| `just` | Run all checks (lint, typecheck, security, test) |
| `just lint` | Run Ruff linter |
| `just lint-fix` | Auto-fix linting issues |
| `just format` | Auto-format code |
| `just typecheck` | Run MyPy type checker |
| `just security` | Run Bandit security scanner |

### Testing

| Command | Description |
|---------|-------------|
| `just test` | Run unit + integration tests (excludes E2E) |
| `just test-unit` | Run unit tests only |
| `just test-integration` | Run fast integration tests |
| `just test-e2e` | Run E2E tests (requires Docker) |
| `just test-all` | Run all tests including E2E |

### Backends

| Command | Description |
|---------|-------------|
| `just start-phoenix` | Start Phoenix backend |
| `just start-mlflow` | Start MLflow backend |
| `just start-backends` | Start all backends |
| `just stop-backends` | Stop all backends |

### E2E Test Infrastructure

| Command | Description |
|---------|-------------|
| `just start-test-backends` | Start test backends (different ports) |
| `just stop-test-backends` | Stop test backends |
| `just test-e2e-full` | Start backends, run E2E, stop backends |

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Google AI API key (required for examples) |
| `LLMOPS_BACKEND` | Override backend selection (`phoenix` or `mlflow`) |
| `LLMOPS_CONFIG` | Path to config file (default: `./llmops.yaml`) |

### Backend Ports

| Service | Development | E2E Tests |
|---------|-------------|-----------|
| Phoenix | 6006 | 16006 |
| MLflow | 5001 | 15001 |

## Coding with Agents

When using AI coding agents (Claude, Cursor, etc.) with this codebase, agents should follow the guidelines in `AGENTS.md`.

### Key Rule: Run Quality Checks After Every Code Change

```bash
just
```

This single command runs all quality checks:
- **Ruff** (linting)
- **MyPy** (type checking)
- **Bandit** (security scanning)
- **Pytest** (tests)

**All checks must pass.** Do not skip or ignore failures.

### Agent Guidelines Summary

1. **Run `just` after every code change** (non-negotiable)
2. Read code before modifying it
3. Ask for clarification when requirements are ambiguous
4. Keep solutions simple (this is a POC)
5. Update examples when code changes
6. The PRD in `./docs/` is the source of truth

### Loading Context

When working with AI agents, the `just` command output provides immediate feedback on:
- Linting errors with file locations
- Type errors with exact positions
- Security issues to address
- Failing tests with stack traces

This allows agents to quickly identify and fix issues without additional exploration.

## Project Structure

```
llmOps/
├── Justfile                 # Root task runner (delegates to SDK)
├── README.md                # This file
├── docs/                    # Architecture & specification docs
├── docker/                  # Root docker-compose
└── llm-observability-sdk/   # SDK implementation
    ├── src/llmops/          # SDK source code
    ├── tests/               # Test suite
    │   ├── test_configure.py    # Unit tests
    │   └── integration/         # Integration + E2E tests
    ├── examples/            # Usage examples
    │   └── server.py            # FastAPI demo server
    ├── docker/              # SDK docker compose files
    ├── llmops.yaml          # Example configuration
    ├── Justfile             # SDK task runner recipes
    └── pyproject.toml       # Project metadata
```

## Documentation

See the `docs/` directory for detailed documentation:

| Document | Description |
|----------|-------------|
| `PRD.md` | Product requirements (source of truth) |
| `CONCEPTUAL_ARCHITECTURE.md` | System overview and design |
| `REFERENCE_ARCHITECTURE.md` | Technical patterns |
| `API_SPECIFICATION.md` | API contracts |
| `AUTO_INSTRUMENT_SPEC.md` | Auto-instrumentation details |