# Root Justfile for LLM Ops Repository
# Run `just` to see available commands, or `just <recipe>` for individual recipes
# Run `just --list` to see all available recipes organized by group

# Settings
set dotenv-load := true
set positional-arguments := true

# Default recipe runs all quality checks (same as SDK default)
default:
    @just sdk default

# Install all dependencies
[group('dev')]
install:
    cd llm-observability-sdk && uv sync --all-extras

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
# SDK Commands (delegated)
# =============================================================================

# Delegate any command to the SDK Justfile
# Usage: just sdk <recipe> [args...]
[group('sdk')]
sdk *args:
    cd llm-observability-sdk && just {{args}}

# =============================================================================
# Common Aliases (convenience shortcuts)
# =============================================================================

# Run all quality checks (lint, typecheck, security, test)
[group('quality')]
check:
    @just sdk default

# Run Ruff linter
[group('quality')]
lint:
    @just sdk lint

# Run Ruff linter with auto-fix
[group('quality')]
lint-fix:
    @just sdk lint-fix

# Run Ruff formatter
[group('quality')]
format:
    @just sdk format

# Check formatting without changes
[group('quality')]
format-check:
    @just sdk format-check

# Run MyPy type checker
[group('quality')]
typecheck:
    @just sdk typecheck

# Run Bandit security scanner
[group('quality')]
security:
    @just sdk security

# =============================================================================
# Testing Aliases
# =============================================================================

# Run all tests (unit + fast integration, excludes E2E)
[group('test')]
test:
    @just sdk test

# Run unit tests only
[group('test')]
test-unit:
    @just sdk test-unit

# Run fast integration tests
[group('test')]
test-integration:
    @just sdk test-integration

# Run E2E tests (requires Docker)
[group('test')]
test-e2e:
    @just sdk test-e2e

# Run all tests including E2E
[group('test')]
test-all:
    @just sdk test-all

# =============================================================================
# Backend Aliases
# =============================================================================

# Start Phoenix backend
[group('server')]
start-phoenix:
    @just sdk start-phoenix

# Start MLflow backend
[group('server')]
start-mlflow:
    @just sdk start-mlflow

# Start all backends
[group('server')]
start-backends:
    @just sdk start-backends

# Stop all backends
[group('server')]
stop-backends:
    @just sdk stop-backends

# =============================================================================
# Development Aliases
# =============================================================================

# Run example server
[group('dev')]
run-example backend="":
    @just sdk run-example {{backend}}

# Start test backends (for E2E)
[group('dev')]
start-test-backends:
    @just sdk start-test-backends

# Stop test backends
[group('dev')]
stop-test-backends:
    @just sdk stop-test-backends

# Run full E2E workflow (start backends, test, stop)
[group('dev')]
test-e2e-full:
    @just sdk test-e2e-full

# =============================================================================
# Example Endpoints
# =============================================================================

# Test /chat endpoint
[group('examples')]
chat message="What is the capital of France?":
    cd llm-observability-sdk && just chat message='{{message}}'

# Test /travel endpoint
[group('examples')]
travel query="Plan a weekend trip to Tokyo":
    cd llm-observability-sdk && just travel query='{{query}}'

# Test /code endpoint
[group('examples')]
code task="generate" prompt="Write a Python function to calculate fibonacci numbers":
    cd llm-observability-sdk && just code task='{{task}}' prompt='{{prompt}}'

# Test /research endpoint
[group('examples')]
research topic="quantum computing applications":
    cd llm-observability-sdk && just research topic='{{topic}}'

# Test /stream endpoint
[group('examples')]
stream prompt="Explain how photosynthesis works":
    cd llm-observability-sdk && just stream prompt='{{prompt}}'

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
    cd llm-observability-sdk && just --list
