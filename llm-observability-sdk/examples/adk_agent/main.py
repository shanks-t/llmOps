"""
Google ADK Agent Example

This app uses the Google Agent Development Kit (ADK) which provides:
- Automatic trace hierarchy (invocation -> agent_run -> call_llm -> execute_tool)
- Built-in tool execution framework
- Session management

Auto-instrumentation:
- Phoenix: Uses OpenInference semantic conventions
- MLflow: Uses MLflow native autolog

Prerequisites:
    1. Start backend: cd docker && docker-compose up -d
    2. Set GOOGLE_API_KEY environment variable
    3. Install deps: pip install llmops[phoenix] google-adk
       OR: pip install llmops[mlflow] google-adk

Run:
    LLMOPS_BACKEND=phoenix python examples/adk_agent/main.py
    LLMOPS_BACKEND=mlflow python examples/adk_agent/main.py

View traces:
    Phoenix: http://localhost:6006
    MLflow: http://localhost:5001
"""

import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

import asyncio
import llmops

# Configure based on environment variable
BACKEND = os.getenv("LLMOPS_BACKEND", "phoenix")

if BACKEND == "phoenix":
    llmops.configure(
        backend="phoenix",
        endpoint="http://localhost:6006/v1/traces",
        service_name="adk-travel-agent",
        console=True,
    )
elif BACKEND == "mlflow":
    llmops.configure(
        backend="mlflow",
        endpoint="http://localhost:5001",
        service_name="adk-travel-agent",
        console=True,
    )
else:
    raise ValueError(f"Unknown backend: {BACKEND}. Use 'phoenix' or 'mlflow'.")

from google import genai
from google.genai import types
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from datetime import datetime, timezone, timedelta


# =============================================================================
# TOOL FUNCTIONS - ADK will auto-instrument these
# =============================================================================

def get_weather(city: str) -> dict:
    """Get current weather for a city.

    Args:
        city: The name of the city to get weather for.

    Returns:
        Weather information including temperature, condition, and humidity.
    """
    weather_db = {
        "paris": {"temp": 22, "condition": "Sunny", "humidity": 45},
        "london": {"temp": 15, "condition": "Cloudy", "humidity": 70},
        "tokyo": {"temp": 28, "condition": "Humid", "humidity": 80},
        "new york": {"temp": 20, "condition": "Partly cloudy", "humidity": 55},
        "sydney": {"temp": 18, "condition": "Clear", "humidity": 50},
    }
    result = weather_db.get(city.lower(), {"temp": 20, "condition": "Unknown", "humidity": 50})
    result["city"] = city
    return result


def get_local_time(city: str) -> dict:
    """Get current local time in a city.

    Args:
        city: The name of the city to get local time for.

    Returns:
        Local time information including time, date, and timezone.
    """
    offsets = {"paris": 1, "london": 0, "tokyo": 9, "new york": -5, "sydney": 11}
    offset = offsets.get(city.lower(), 0)
    local_time = datetime.now(timezone(timedelta(hours=offset)))
    return {
        "city": city,
        "time": local_time.strftime("%H:%M"),
        "date": local_time.strftime("%Y-%m-%d"),
        "timezone": f"UTC{'+' if offset >= 0 else ''}{offset}"
    }


def get_attractions(city: str) -> dict:
    """Get top tourist attractions in a city.

    Args:
        city: The name of the city to get attractions for.

    Returns:
        List of top attractions in the city.
    """
    attractions_db = {
        "paris": ["Eiffel Tower", "Louvre Museum", "Notre-Dame", "Champs-Élysées"],
        "london": ["Big Ben", "Tower of London", "British Museum", "Buckingham Palace"],
        "tokyo": ["Tokyo Tower", "Senso-ji Temple", "Shibuya Crossing", "Meiji Shrine"],
        "new york": ["Statue of Liberty", "Central Park", "Times Square", "Empire State Building"],
        "sydney": ["Sydney Opera House", "Harbour Bridge", "Bondi Beach", "Taronga Zoo"],
    }
    return {
        "city": city,
        "attractions": attractions_db.get(city.lower(), ["Local landmarks"])
    }


def get_flight_prices(origin: str, destination: str) -> dict:
    """Get estimated flight prices between two cities.

    Args:
        origin: The departure city.
        destination: The arrival city.

    Returns:
        Flight price estimates for different classes.
    """
    import random
    base_price = random.randint(200, 800)
    return {
        "origin": origin,
        "destination": destination,
        "economy": f"${base_price}",
        "business": f"${base_price * 3}",
        "first_class": f"${base_price * 5}",
    }


def get_hotels(city: str, budget: str = "medium") -> dict:
    """Get hotel recommendations in a city.

    Args:
        city: The name of the city.
        budget: Budget level - "budget", "medium", or "luxury".

    Returns:
        Hotel recommendations based on budget.
    """
    hotels_db = {
        "paris": {
            "budget": ["Ibis Paris", "Hotel F1"],
            "medium": ["Novotel Paris", "Mercure Paris"],
            "luxury": ["Ritz Paris", "Four Seasons George V"],
        },
        "tokyo": {
            "budget": ["APA Hotel", "Toyoko Inn"],
            "medium": ["Hotel Gracery", "Mitsui Garden"],
            "luxury": ["Park Hyatt Tokyo", "Aman Tokyo"],
        },
    }
    city_hotels = hotels_db.get(city.lower(), {
        "budget": ["Budget Hotel"],
        "medium": ["Standard Hotel"],
        "luxury": ["Luxury Resort"],
    })
    return {
        "city": city,
        "budget": budget,
        "recommendations": city_hotels.get(budget, city_hotels["medium"])
    }


# =============================================================================
# ADK AGENT SETUP
# =============================================================================

# Create the travel agent with tools
travel_agent = Agent(
    name="travel_assistant",
    model="gemini-2.0-flash-exp",
    description="A helpful travel assistant that can provide weather, time, attractions, flights, and hotel information.",
    instruction="""You are a helpful travel assistant. When users ask about travel destinations:
    1. Use the available tools to gather relevant information
    2. Provide comprehensive and helpful responses
    3. Be friendly and informative

    Available tools:
    - get_weather: Get current weather for a city
    - get_local_time: Get current local time in a city
    - get_attractions: Get top tourist attractions
    - get_flight_prices: Get flight price estimates
    - get_hotels: Get hotel recommendations
    """,
    tools=[get_weather, get_local_time, get_attractions, get_flight_prices, get_hotels],
)


async def run_agent(query: str) -> str:
    """Run the travel agent with a query."""
    # Create session service and runner
    session_service = InMemorySessionService()
    runner = Runner(
        agent=travel_agent,
        app_name="travel_app",
        session_service=session_service,
    )

    # Create a session
    session = await session_service.create_session(
        app_name="travel_app",
        user_id="demo_user",
    )

    # Run the agent
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}\n")

    # Create a Content object with the user message
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="demo_user",
        session_id=session.id,
        new_message=user_message,
    ):
        # Collect the final response
        if hasattr(event, 'content') and event.content:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    response_text += part.text

    return response_text


async def main():
    """Run example queries to demonstrate auto-instrumentation."""

    print("\n" + "="*60)
    print("ADK Agent Auto-Instrumentation Demo")
    print("="*60)
    print("\nThis demo shows how ADK automatically creates trace hierarchy:")
    print("  invocation -> agent_run -> call_llm / execute_tool")
    print("\nWatch the console output for span details.\n")

    # Test queries
    queries = [
        "What's the weather like in Tokyo?",
        "I'm planning a trip to Paris. What should I know about the weather, attractions, and hotels?",
    ]

    for query in queries:
        try:
            response = await run_agent(query)
            print(f"\nResponse: {response[:500]}...")
            print(f"\n{'='*60}\n")
        except Exception as e:
            print(f"Error: {e}")

    # Flush traces
    llmops.shutdown()


if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY environment variable not set")
        exit(1)

    asyncio.run(main())
