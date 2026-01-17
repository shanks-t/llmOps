# Root Justfile for LLM Ops Repository
# Run `just` to see available commands, or `just <recipe>` for individual recipes.
# Run `just --list` to see all available recipes organized by group.
#
# Approach
# - Root is the single entry point for all developer workflows.
# - Nested services are exposed via `mod` modules and root aliases.
# - Use `sdk::recipe` or `genai::recipe` for full access, or root aliases like
#   `sdk-lint`, `genai-run`, and `all-light` for convenience.
# - Keep paths relative so the Justfiles work on any developer machine.
#
# Manual
# https://just.systems/man/en/
#
# Quickstart
# - Run lightweight checks: `just` or `just all-light`
# - Run SDK unit tests: `just sdk-test-unit`
# - Run GenAI service: `just genai-run`
# - Send a request: `just genai::chat`
#
# Module Pattern
# This Justfile exposes child Justfiles as modules.
# - `just sdk::recipe` maps to llm-observability-sdk/Justfile
# - `just genai::recipe` maps to llm-observability-sdk/examples/genai_service/Justfile
#
# For example commands (chat, travel, etc.), pass arguments positionally.
# Use: `just chat "Hello"` not `just chat message="Hello"`

# Settings
set dotenv-load := true
set positional-arguments := true

mod sdk "llm-observability-sdk/Justfile"
mod genai "llm-observability-sdk/examples/genai_service/Justfile"

# Default recipe runs lightweight checks across projects
[doc('Run lightweight checks for SDK and GenAI')]
all-light: sdk::lint sdk::typecheck sdk::security sdk::test-unit genai::lint genai::typecheck genai::format-check

default: all-light

# Install all dependencies
[group('dev')]
install:
    just sdk::install

# Show available recipes, optionally filtered by group
# Usage: just list [group]
[group('info')]
list group="":
    #!/usr/bin/env bash
    if [ -z "{{group}}" ]; then
        just --list
    else
        just --list | awk -v grp="{{group}}" '$0 ~ "\\[" grp "\\]" {found=1; print; next} /^    \[/ {found=0} found'
    fi

# =============================================================================
# SDK Commands (modules)
# =============================================================================

# Delegate commands to the SDK Justfile via module
# Usage: just sdk::recipe [args...]
# Example: just sdk::test

# =============================================================================
# GenAI Service Commands (modules)
# =============================================================================

# Delegate commands to the GenAI Service Justfile via module
# Usage: just genai::recipe [args...]
# Example: just genai::run

# Run GenAI service
[group('genai')]
genai-run: genai::run

# Run GenAI service with debug output
[group('genai')]
genai-run-debug: genai::run-debug

# Run GenAI quality checks (lint + typecheck)
[group('genai')]
genai-check: genai::check

# Start Jaeger for GenAI service
[group('genai')]
genai-start-jaeger: genai::start-jaeger

# Install GenAI service dependencies
[group('genai')]
genai-install: genai::install

# Show GenAI service recipes
[group('info')]
genai-recipes:
    just --list genai

# =============================================================================
# Common Aliases (convenience shortcuts)
# =============================================================================

# Run all quality checks (lightweight across projects)
[group('quality')]
check: all-light

# SDK - Ruff linter
[group('quality')]
sdk-lint: sdk::lint

# SDK - Ruff linter with auto-fix
[group('quality')]
sdk-lint-fix: sdk::lint-fix

# SDK - Ruff formatter
[group('quality')]
sdk-format: sdk::format

# SDK - Check formatting without changes
[group('quality')]
sdk-format-check: sdk::format-check

# SDK - MyPy type checker
[group('quality')]
sdk-typecheck: sdk::typecheck

# SDK - Bandit security scanner
[group('quality')]
sdk-security: sdk::security

# GenAI - Ruff linter
[group('quality')]
genai-lint: genai::lint

# GenAI - Ruff formatter
[group('quality')]
genai-format: genai::format

# GenAI - Check formatting without changes
[group('quality')]
genai-format-check: genai::format-check

# GenAI - MyPy type checker
[group('quality')]
genai-typecheck: genai::typecheck

# =============================================================================
# Testing Aliases
# =============================================================================

# SDK - Run all tests (unit + fast integration, excludes E2E)
[group('test')]
sdk-test: sdk::test

# SDK - Run unit tests only
[group('test')]
sdk-test-unit: sdk::test-unit

# SDK - Run fast integration tests
[group('test')]
sdk-test-integration: sdk::test-integration

# SDK - Run E2E tests (requires Docker)
[group('test')]
sdk-test-e2e: sdk::test-e2e

# SDK - Run all tests including E2E
[group('test')]
sdk-test-all: sdk::test-all

# =============================================================================
# Backend Aliases
# =============================================================================

# Start Phoenix backend
[group('server')]
start-phoenix: sdk::start-phoenix

# Start all backends
[group('server')]
start-backends: sdk::start-backends

# Stop all backends
[group('server')]
stop-backends: sdk::stop-backends

# =============================================================================
# Development Aliases
# =============================================================================

# Run example server
[group('dev')]
run-example backend="":
    just sdk::run-example {{backend}}

# Start test backends (for E2E)
[group('dev')]
start-test-backends: sdk::start-test-backends

# Stop test backends
[group('dev')]
stop-test-backends: sdk::stop-test-backends

# Run full E2E workflow (start backends, test, stop)
[group('dev')]
test-e2e-full: sdk::test-e2e-full

# =============================================================================
# Example Endpoints
# =============================================================================
# Note: Pass arguments positionally (e.g., `just chat "Hello"`)
# Named args like `just chat message="Hello"` will be mangled during delegation.

# Test /chat endpoint
[group('examples')]
chat message="What is the capital of France?":
    just sdk::chat '{{message}}'

# Test /travel endpoint
[group('examples')]
travel query="Plan a weekend trip to Tokyo":
    just sdk::travel '{{query}}'

# Test /code endpoint (usage: just code "generate" "Write a fibonacci function")
[group('examples')]
code task="generate" prompt="Write a Python function to calculate fibonacci numbers":
    just sdk::code '{{task}}' '{{prompt}}'

# Test /research endpoint
[group('examples')]
research topic="quantum computing applications":
    just sdk::research '{{topic}}'

# Test /stream endpoint
[group('examples')]
stream prompt="Explain how photosynthesis works":
    just sdk::stream '{{prompt}}'

# =============================================================================
# Repository Info
# =============================================================================

# Show project structure
[group('info')]
tree:
    tree -L 3 -I '__pycache__|*.pyc|.git|.venv|node_modules|*.egg-info'

# Show SDK Justfile recipes
[group('info')]
sdk-recipes:
    just --list sdk
