"""
LLMOps Demo - Minimal FastAPI service demonstrating llmops.instrument()

This example shows how to use the llmops SDK for auto-instrumentation
of Google ADK with a simple YAML configuration file.

Run:
    cd examples/llmops_demo
    uv run uvicorn main:app --reload

View traces:
    Phoenix: http://localhost:6006

Prerequisites:
    1. Start Phoenix: cd docker && docker-compose up -d phoenix
    2. Set GOOGLE_API_KEY environment variable
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

import llmops

load_dotenv()

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ChatRequest(BaseModel):
    message: str
    context: str | None = None  # Optional context for grounded/faithful responses


class ChatResponse(BaseModel):
    message: str
    response: str
    context: str | None = None  # Echo back context if provided


# =============================================================================
# APP & LIFESPAN
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize llmops telemetry on startup, shutdown on exit."""
    # Get the config path relative to this file
    config_path = Path(__file__).parent / "llmops.yaml"

    # Initialize telemetry using the llmops SDK
    llmops.instrument(config=config_path)

    print(f"[llmops_demo] Telemetry initialized with config: {config_path}")

    yield

    # Shutdown and flush traces
    llmops.shutdown()
    print("[llmops_demo] Telemetry shutdown complete")


app = FastAPI(
    title="LLMOps Demo",
    description="Minimal example demonstrating llmops.instrument() for auto-instrumentation",
    version="0.1.0",
    lifespan=lifespan,
)


# =============================================================================
# ROUTES
# =============================================================================


@app.get("/")
async def root():
    """Service information."""
    return {
        "service": "LLMOps Demo",
        "version": "0.1.0",
        "description": "Minimal example using llmops.instrument() for telemetry",
        "endpoints": {
            "POST /chat": "Chat with the assistant (supports weather and time queries)",
            "GET /health": "Health check",
        },
        "observability": {
            "config": "llmops.yaml",
            "traces": "http://localhost:6006",
        },
    }


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "google_api_key": "configured" if os.getenv("GOOGLE_API_KEY") else "missing",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the assistant.

    The assistant can help with weather and time queries for various cities.
    Optionally provide context to get grounded responses (useful for testing
    faithfulness/hallucination evaluation).

    Examples:
        - "What's the weather in Paris?"
        - "What time is it in Tokyo?"
        - "Tell me the weather and time in London"

    With context (for faithfulness evaluation):
        {
            "message": "What is the capital of France?",
            "context": "Paris is the capital and largest city of France."
        }
    """
    # Import here to avoid circular imports and ensure instrumentation is applied
    from agents import assistant_agent, run_agent

    response = await run_agent(
        assistant_agent,
        request.message,
        context=request.context,
    )
    return ChatResponse(
        message=request.message,
        response=response,
        context=request.context,
    )
