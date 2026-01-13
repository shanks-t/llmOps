"""
FastAPI + Google ADK Test Application

This app tests the llmops SDK auto-instrumentation with:
- FastAPI web framework
- Google ADK agent with tools
- Gemini LLM

Prerequisites:
    1. Start backends: cd docker && docker-compose up -d
    2. Set GOOGLE_API_KEY environment variable
    3. Install deps: pip install llmops[phoenix] fastapi uvicorn google-adk

Run:
    uvicorn main:app --reload

Test:
    curl "http://localhost:8000/ask?query=What%20is%20the%20weather%20in%20Paris"

View traces:
    Phoenix: http://localhost:6006
    MLflow: http://localhost:5001
"""

import os
import llmops

# =============================================================================
# CONFIGURE BACKEND - Set LLMOPS_BACKEND env var: phoenix, mlflow, or both
# =============================================================================
BACKEND = os.getenv("LLMOPS_BACKEND", "both")

if BACKEND == "phoenix":
    llmops.configure(
        backend="phoenix",
        endpoint="http://localhost:6006/v1/traces",
        service_name="fastapi-adk-demo",
    )
elif BACKEND == "mlflow":
    llmops.configure(
        backend="mlflow",
        endpoint="http://localhost:5001",
        service_name="fastapi-adk-demo",
    )
elif BACKEND == "both":
    # Multi-backend: send traces to both Phoenix and MLflow
    llmops.configure(
        backends=[
            {"type": "phoenix", "endpoint": "http://localhost:6006/v1/traces"},
            {"type": "mlflow", "endpoint": "http://localhost:5001"},
        ],
        service_name="fastapi-adk-demo",
    )

# =============================================================================
# APPLICATION CODE - This is unchanged regardless of backend
# =============================================================================
from fastapi import FastAPI

app = FastAPI(title="FastAPI ADK Demo")


# Tool functions for the agent
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    weather_data = {
        "paris": "Sunny, 22°C",
        "london": "Cloudy, 15°C",
        "tokyo": "Rainy, 18°C",
        "new york": "Partly cloudy, 20°C",
    }
    return weather_data.get(city.lower(), f"Weather data not available for {city}")


def get_time(city: str) -> str:
    """Get the current time in a city."""
    from datetime import datetime, timezone, timedelta

    offsets = {"paris": 1, "london": 0, "tokyo": 9, "new york": -5}
    offset = offsets.get(city.lower(), 0)
    time = datetime.now(timezone(timedelta(hours=offset)))
    return f"Current time in {city}: {time.strftime('%H:%M')}"


# Create GenAI client (lazy initialization)
_client = None


def get_client():
    """Get or create the Google GenAI client."""
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client()
    return _client


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "backend": BACKEND,
        "message": "Use /ask?query=... to interact with the agent",
    }


@app.get("/ask")
async def ask(query: str):
    """
    Ask the agent a question.

    Example: /ask?query=What is the weather in Paris?
    """
    if not os.getenv("GOOGLE_API_KEY"):
        return {"error": "GOOGLE_API_KEY environment variable not set"}

    try:
        client = get_client()

        # Simple chat with Gemini (instrumented by OpenInference/MLflow)
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=query,
        )
        return {"query": query, "response": response.text}
    except Exception as e:
        return {"error": str(e)}


@app.on_event("shutdown")
def shutdown_event():
    """Flush traces on shutdown."""
    llmops.shutdown()


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
