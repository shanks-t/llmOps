"""
agents.py

Single Google ADK agent with tool calls for the LLMOps demo.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# =============================================================================
# TOOL FUNCTIONS
# =============================================================================


def get_weather(city: str) -> dict:
    """Get current weather for a city.

    Args:
        city: The name of the city to get weather for.

    Returns:
        Weather information including temperature, condition, and humidity.
    """
    weather_data = {
        "paris": {"temp_c": 18, "condition": "Partly Cloudy", "humidity": 65},
        "london": {"temp_c": 14, "condition": "Rainy", "humidity": 80},
        "tokyo": {"temp_c": 26, "condition": "Sunny", "humidity": 70},
        "new york": {"temp_c": 22, "condition": "Clear", "humidity": 55},
        "sydney": {"temp_c": 20, "condition": "Sunny", "humidity": 60},
    }
    result = weather_data.get(
        city.lower(),
        {"temp_c": 20, "condition": "Unknown", "humidity": 50},
    )
    return {"city": city, **result}


def get_time(city: str) -> dict:
    """Get current local time in a city.

    Args:
        city: The name of the city to get local time for.

    Returns:
        Local time information including time, date, and timezone.
    """
    offsets = {
        "paris": 1,
        "london": 0,
        "tokyo": 9,
        "new york": -5,
        "sydney": 11,
    }
    offset = offsets.get(city.lower(), 0)
    local_time = datetime.now(timezone(timedelta(hours=offset)))
    return {
        "city": city,
        "time": local_time.strftime("%H:%M"),
        "date": local_time.strftime("%Y-%m-%d"),
        "timezone": f"UTC{'+' if offset >= 0 else ''}{offset}",
    }


# =============================================================================
# AGENT DEFINITION
# =============================================================================


assistant_agent = Agent(
    name="assistant",
    model="gemini-2.0-flash",
    description="A helpful assistant that can check weather and time.",
    instruction="""You are a helpful assistant. You can help users with:
    1. Getting weather information for cities using the get_weather tool
    2. Getting the current time in cities using the get_time tool

    When asked about weather or time, always use the appropriate tool.

    IMPORTANT: If the user provides context/reference information, base your
    response ONLY on that context. Do not add information not present in the
    context. This is critical for grounded, faithful responses.

    Be concise and friendly in your responses.""",
    tools=[get_weather, get_time],
)


# =============================================================================
# SESSION & RUNNER
# =============================================================================


session_service = InMemorySessionService()


def create_runner(agent: Agent) -> Runner:
    """Create a runner for an agent."""
    return Runner(
        agent=agent,
        app_name="llmops_demo",
        session_service=session_service,
    )


async def run_agent(
    agent: Agent,
    query: str,
    user_id: str = "default",
    context: str | None = None,
) -> str:
    """Run an agent and collect the response.

    Args:
        agent: The agent to run.
        query: User's input message.
        user_id: User identifier for session management.
        context: Optional context for grounded responses. When provided,
                 the agent is instructed to base its response only on this
                 context. Useful for testing faithfulness/hallucination
                 evaluation.

    Returns:
        The agent's response text.
    """
    runner = create_runner(agent)

    session = await session_service.create_session(
        app_name="llmops_demo",
        user_id=user_id,
    )

    # Format message with context for grounding (enables faithfulness evaluation)
    if context:
        formatted_query = f"""Context (base your response ONLY on this information):
{context}

User Question: {query}

Respond using ONLY the information provided in the context above."""
    else:
        formatted_query = query

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=formatted_query)],
    )

    response_text = ""

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        if hasattr(event, "content") and event.content:
            if event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text

    return response_text
