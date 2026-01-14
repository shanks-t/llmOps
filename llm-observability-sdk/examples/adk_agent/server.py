"""
FastAPI server for the ADK Travel Agent

Run:
    LLMOPS_BACKEND=phoenix uv run uvicorn examples.adk_agent.server:app --reload
    LLMOPS_BACKEND=mlflow uv run uvicorn examples.adk_agent.server:app --reload

Test:
    curl http://localhost:8000/
    curl "http://localhost:8000/chat?query=What%20is%20the%20weather%20in%20Tokyo"
    curl "http://localhost:8000/chat?query=Plan%20a%20trip%20to%20Paris"

View traces:
    Phoenix: http://localhost:6006
    MLflow: http://localhost:5001
"""

import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

import llmops

# Configure based on environment variable
BACKEND = os.getenv("LLMOPS_BACKEND", "phoenix")

if BACKEND == "phoenix":
    llmops.configure(
        backend="phoenix",
        endpoint="http://localhost:6006/v1/traces",
        service_name="adk-travel-agent-v2",
    )
elif BACKEND == "mlflow":
    llmops.configure(
        backend="mlflow",
        endpoint="http://localhost:5001",
        service_name="adk-travel-agent-v2",
    )
else:
    raise ValueError(f"Unknown backend: {BACKEND}")

from fastapi import FastAPI
from google.genai import types
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from datetime import datetime, timezone, timedelta
import uuid

app = FastAPI(title="ADK Travel Agent")

# =============================================================================
# TOOL FUNCTIONS
# =============================================================================


def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    weather_db = {
        "paris": {"temp": 22, "condition": "Sunny", "humidity": 45},
        "london": {"temp": 15, "condition": "Cloudy", "humidity": 70},
        "tokyo": {"temp": 28, "condition": "Humid", "humidity": 80},
        "new york": {"temp": 20, "condition": "Partly cloudy", "humidity": 55},
    }
    result = weather_db.get(
        city.lower(), {"temp": 20, "condition": "Unknown", "humidity": 50}
    )
    result["city"] = city
    return result


def get_attractions(city: str) -> dict:
    """Get top attractions in a city."""
    attractions_db = {
        "paris": ["Eiffel Tower", "Louvre Museum", "Notre-Dame"],
        "london": ["Big Ben", "Tower of London", "British Museum"],
        "tokyo": ["Tokyo Tower", "Senso-ji Temple", "Shibuya Crossing"],
        "new york": ["Statue of Liberty", "Central Park", "Times Square"],
    }
    return {
        "city": city,
        "attractions": attractions_db.get(city.lower(), ["Local landmarks"]),
    }


def get_hotels(city: str, budget: str = "medium") -> dict:
    """Get hotel recommendations."""
    hotels_db = {
        "paris": {"budget": ["Ibis"], "medium": ["Novotel"], "luxury": ["Ritz Paris"]},
        "tokyo": {
            "budget": ["APA Hotel"],
            "medium": ["Hotel Gracery"],
            "luxury": ["Park Hyatt"],
        },
    }
    city_hotels = hotels_db.get(city.lower(), {"medium": ["Standard Hotel"]})
    return {
        "city": city,
        "budget": budget,
        "hotels": city_hotels.get(budget, ["Hotel"]),
    }


# =============================================================================
# ADK AGENT
# =============================================================================

travel_agent = Agent(
    name="travel_assistant",
    model="gemini-2.0-flash-exp",
    instruction="""You are a helpful travel assistant. Use the available tools to answer questions about weather, attractions, and hotels.""",
    tools=[get_weather, get_attractions, get_hotels],
)

session_service = InMemorySessionService()
runner = Runner(
    agent=travel_agent, app_name="travel_app", session_service=session_service
)


# =============================================================================
# ENDPOINTS
# =============================================================================


@app.get("/")
async def root():
    return {
        "status": "ok",
        "backend": BACKEND,
        "endpoints": {
            "/chat": "Send a query to the travel agent",
        },
        "example": "curl 'http://localhost:8000/chat?query=What%20is%20the%20weather%20in%20Paris'",
    }


@app.get("/chat")
async def chat(query: str):
    """Send a query to the ADK travel agent."""
    if not os.getenv("GOOGLE_API_KEY"):
        return {"error": "GOOGLE_API_KEY not set"}

    # For MLflow: create parent span to group all LLM calls
    if BACKEND == "mlflow":
        import mlflow
        return await _chat_with_mlflow_trace(query)
    else:
        return await _chat_impl(query)


async def _chat_with_mlflow_trace(query: str):
    """Chat implementation wrapped with MLflow trace."""
    import mlflow
    with mlflow.start_span(name="adk_agent_chat") as span:
        span.set_inputs({"query": query})
        result = await _chat_impl(query)
        span.set_outputs(result)
        return result


async def _chat_impl(query: str):
    """Core chat implementation."""

    # Create a new session for each request
    session = await session_service.create_session(
        app_name="travel_app",
        user_id="api_user",
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="api_user",
        session_id=session.id,
        new_message=user_message,
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    return {
        "query": query,
        "response": response_text,
        "backend": BACKEND,
    }


@app.on_event("shutdown")
def shutdown_event():
    llmops.shutdown()
