"""
FastAPI + Google GenAI Test Application

This app tests the llmops SDK auto-instrumentation with:
- FastAPI web framework
- Google GenAI with function calling
- Multi-step tool execution
- Nested operations

Prerequisites:
    1. Start backends: cd docker && docker-compose up -d
    2. Set GOOGLE_API_KEY environment variable
    3. Install deps: pip install llmops[phoenix,mlflow] fastapi uvicorn google-genai

Run:
    uvicorn examples.fastapi_adk_app.main:app --reload

Test endpoints:
    curl http://localhost:8000/
    curl "http://localhost:8000/chat?message=Hello"
    curl "http://localhost:8000/weather?city=Paris"
    curl "http://localhost:8000/travel?destination=Tokyo"
    curl "http://localhost:8000/multi-step?query=Plan%20a%20trip%20to%20Paris"

View traces:
    Phoenix: http://localhost:6006
    MLflow: http://localhost:5001
"""

import os
import json
import llmops
from opentelemetry import trace

# =============================================================================
# CONFIGURE BACKEND - Set LLMOPS_BACKEND env var: phoenix, mlflow, or both
# =============================================================================
BACKEND = os.getenv("LLMOPS_BACKEND", "both")

if BACKEND == "phoenix":
    llmops.configure(
        backend="phoenix",
        endpoint="http://localhost:6006/v1/traces",
        service_name="travel-assistant-demo",
    )
elif BACKEND == "mlflow":
    llmops.configure(
        backend="mlflow",
        endpoint="http://localhost:5001",
        service_name="travel-assistant-demo",
    )
elif BACKEND == "both":
    llmops.configure(
        backends=[
            {"type": "phoenix", "endpoint": "http://localhost:6006/v1/traces"},
            {"type": "mlflow", "endpoint": "http://localhost:5001"},
        ],
        service_name="travel-assistant-demo",
    )

# =============================================================================
# APPLICATION CODE
# =============================================================================
from fastapi import FastAPI
from datetime import datetime, timezone, timedelta

app = FastAPI(title="Travel Assistant Demo")
tracer = trace.get_tracer("travel-assistant")


# =============================================================================
# TOOL FUNCTIONS - These simulate external service calls
# =============================================================================

def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    with tracer.start_as_current_span("tool:get_weather") as span:
        span.set_attribute("tool.name", "get_weather")
        span.set_attribute("tool.input.city", city)

        # Simulated weather data
        weather_db = {
            "paris": {"temp": 22, "condition": "Sunny", "humidity": 45},
            "london": {"temp": 15, "condition": "Cloudy", "humidity": 70},
            "tokyo": {"temp": 28, "condition": "Humid", "humidity": 80},
            "new york": {"temp": 20, "condition": "Partly cloudy", "humidity": 55},
            "sydney": {"temp": 18, "condition": "Clear", "humidity": 50},
        }

        result = weather_db.get(city.lower(), {"temp": 20, "condition": "Unknown", "humidity": 50})
        result["city"] = city

        span.set_attribute("tool.output", json.dumps(result))
        return result


def get_local_time(city: str) -> dict:
    """Get current local time in a city."""
    with tracer.start_as_current_span("tool:get_local_time") as span:
        span.set_attribute("tool.name", "get_local_time")
        span.set_attribute("tool.input.city", city)

        # Timezone offsets
        offsets = {
            "paris": 1, "london": 0, "tokyo": 9,
            "new york": -5, "sydney": 11
        }
        offset = offsets.get(city.lower(), 0)
        local_time = datetime.now(timezone(timedelta(hours=offset)))

        result = {
            "city": city,
            "time": local_time.strftime("%H:%M"),
            "date": local_time.strftime("%Y-%m-%d"),
            "timezone": f"UTC{'+' if offset >= 0 else ''}{offset}"
        }

        span.set_attribute("tool.output", json.dumps(result))
        return result


def get_attractions(city: str) -> dict:
    """Get top attractions in a city."""
    with tracer.start_as_current_span("tool:get_attractions") as span:
        span.set_attribute("tool.name", "get_attractions")
        span.set_attribute("tool.input.city", city)

        attractions_db = {
            "paris": ["Eiffel Tower", "Louvre Museum", "Notre-Dame", "Champs-Élysées"],
            "london": ["Big Ben", "Tower of London", "British Museum", "Buckingham Palace"],
            "tokyo": ["Tokyo Tower", "Senso-ji Temple", "Shibuya Crossing", "Meiji Shrine"],
            "new york": ["Statue of Liberty", "Central Park", "Times Square", "Empire State Building"],
            "sydney": ["Sydney Opera House", "Harbour Bridge", "Bondi Beach", "Taronga Zoo"],
        }

        result = {
            "city": city,
            "attractions": attractions_db.get(city.lower(), ["Local landmarks"])
        }

        span.set_attribute("tool.output", json.dumps(result))
        return result


def get_flight_prices(origin: str, destination: str) -> dict:
    """Get estimated flight prices."""
    with tracer.start_as_current_span("tool:get_flight_prices") as span:
        span.set_attribute("tool.name", "get_flight_prices")
        span.set_attribute("tool.input.origin", origin)
        span.set_attribute("tool.input.destination", destination)

        # Simulated price calculation
        import random
        base_price = random.randint(200, 800)

        result = {
            "origin": origin,
            "destination": destination,
            "economy": f"${base_price}",
            "business": f"${base_price * 3}",
            "first_class": f"${base_price * 5}",
        }

        span.set_attribute("tool.output", json.dumps(result))
        return result


def get_hotels(city: str, budget: str = "medium") -> dict:
    """Get hotel recommendations."""
    with tracer.start_as_current_span("tool:get_hotels") as span:
        span.set_attribute("tool.name", "get_hotels")
        span.set_attribute("tool.input.city", city)
        span.set_attribute("tool.input.budget", budget)

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

        result = {
            "city": city,
            "budget": budget,
            "recommendations": city_hotels.get(budget, city_hotels["medium"])
        }

        span.set_attribute("tool.output", json.dumps(result))
        return result


# =============================================================================
# GENAI CLIENT
# =============================================================================

_client = None

def get_client():
    """Get or create the Google GenAI client."""
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client()
    return _client


# Define tools for function calling
TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "get_local_time",
        "description": "Get the current local time in a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "get_attractions",
        "description": "Get top tourist attractions in a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "get_flight_prices",
        "description": "Get estimated flight prices between two cities",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Origin city"},
                "destination": {"type": "string", "description": "Destination city"}
            },
            "required": ["origin", "destination"]
        }
    },
    {
        "name": "get_hotels",
        "description": "Get hotel recommendations in a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name"},
                "budget": {"type": "string", "enum": ["budget", "medium", "luxury"], "description": "Budget level"}
            },
            "required": ["city"]
        }
    },
]

TOOL_FUNCTIONS = {
    "get_weather": get_weather,
    "get_local_time": get_local_time,
    "get_attractions": get_attractions,
    "get_flight_prices": get_flight_prices,
    "get_hotels": get_hotels,
}


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Health check and API info."""
    return {
        "status": "ok",
        "backend": BACKEND,
        "endpoints": {
            "/chat": "Simple chat with Gemini",
            "/weather": "Get weather for a city",
            "/travel": "Get travel info (weather + time + attractions)",
            "/multi-step": "Complex multi-step query with function calling",
        }
    }


@app.get("/chat")
async def chat(message: str):
    """Simple chat endpoint - single LLM call."""
    if not os.getenv("GOOGLE_API_KEY"):
        return {"error": "GOOGLE_API_KEY not set"}

    with tracer.start_as_current_span("endpoint:chat") as span:
        span.set_attribute("user.message", message)

        try:
            client = get_client()
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=message,
            )

            span.set_attribute("llm.response_length", len(response.text))
            return {"message": message, "response": response.text}
        except Exception as e:
            span.set_attribute("error", str(e))
            return {"error": str(e)}


@app.get("/weather")
async def weather_endpoint(city: str):
    """Get weather for a city - uses tool function."""
    with tracer.start_as_current_span("endpoint:weather") as span:
        span.set_attribute("request.city", city)

        result = get_weather(city)
        return result


@app.get("/travel")
async def travel_info(destination: str):
    """Get comprehensive travel info - multiple parallel tool calls."""
    with tracer.start_as_current_span("endpoint:travel") as span:
        span.set_attribute("request.destination", destination)

        # Call multiple tools
        weather = get_weather(destination)
        time = get_local_time(destination)
        attractions = get_attractions(destination)

        return {
            "destination": destination,
            "weather": weather,
            "local_time": time,
            "attractions": attractions,
        }


@app.get("/multi-step")
async def multi_step_query(query: str):
    """
    Complex multi-step query with LLM and function calling.

    This demonstrates a full agentic workflow:
    1. LLM analyzes the query
    2. LLM decides which tools to call
    3. Tools are executed
    4. LLM synthesizes final response
    """
    if not os.getenv("GOOGLE_API_KEY"):
        return {"error": "GOOGLE_API_KEY not set"}

    with tracer.start_as_current_span("endpoint:multi_step") as span:
        span.set_attribute("user.query", query)

        try:
            client = get_client()

            # Step 1: Initial LLM call to understand intent and plan
            with tracer.start_as_current_span("step:analyze_query") as analyze_span:
                analyze_span.set_attribute("step", "analyze")

                system_prompt = """You are a helpful travel assistant.
                Analyze the user's query and respond with a JSON plan.
                Include which information you need: weather, time, attractions, flights, hotels.
                Format: {"needs": ["weather", "time", ...], "city": "...", "summary": "..."}"""

                analysis = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=f"{system_prompt}\n\nUser query: {query}",
                )
                analyze_span.set_attribute("llm.response", analysis.text[:500])

            # Step 2: Parse and execute tools
            tool_results = {}
            with tracer.start_as_current_span("step:execute_tools") as tools_span:
                tools_span.set_attribute("step", "execute_tools")

                # Simple parsing - in production use proper JSON parsing
                text = analysis.text.lower()
                city = None

                # Extract city from query
                for c in ["paris", "london", "tokyo", "new york", "sydney"]:
                    if c in query.lower():
                        city = c.title()
                        break

                if not city:
                    city = "Paris"  # Default

                tools_span.set_attribute("detected.city", city)

                # Execute relevant tools based on keywords
                if "weather" in text or "temperature" in query.lower():
                    tool_results["weather"] = get_weather(city)

                if "time" in text or "when" in query.lower():
                    tool_results["time"] = get_local_time(city)

                if "attraction" in text or "visit" in query.lower() or "see" in query.lower():
                    tool_results["attractions"] = get_attractions(city)

                if "flight" in text or "fly" in query.lower():
                    tool_results["flights"] = get_flight_prices("New York", city)

                if "hotel" in text or "stay" in query.lower():
                    tool_results["hotels"] = get_hotels(city, "medium")

                # If nothing matched, get basic info
                if not tool_results:
                    tool_results["weather"] = get_weather(city)
                    tool_results["attractions"] = get_attractions(city)

                tools_span.set_attribute("tools.executed", list(tool_results.keys()))

            # Step 3: Synthesize final response
            with tracer.start_as_current_span("step:synthesize") as synth_span:
                synth_span.set_attribute("step", "synthesize")

                synthesis_prompt = f"""Based on the following information, provide a helpful response to: "{query}"

                Data collected:
                {json.dumps(tool_results, indent=2)}

                Provide a natural, conversational response summarizing this information."""

                final_response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=synthesis_prompt,
                )
                synth_span.set_attribute("llm.response_length", len(final_response.text))

            span.set_attribute("tools.count", len(tool_results))

            return {
                "query": query,
                "tool_results": tool_results,
                "response": final_response.text,
            }

        except Exception as e:
            span.set_attribute("error", str(e))
            return {"error": str(e)}


@app.get("/streaming")
async def streaming_chat(message: str):
    """Streaming response example."""
    if not os.getenv("GOOGLE_API_KEY"):
        return {"error": "GOOGLE_API_KEY not set"}

    with tracer.start_as_current_span("endpoint:streaming") as span:
        span.set_attribute("user.message", message)

        try:
            client = get_client()

            # Use streaming
            chunks = []
            for chunk in client.models.generate_content_stream(
                model="gemini-2.0-flash-exp",
                contents=message,
            ):
                if chunk.text:
                    chunks.append(chunk.text)

            full_response = "".join(chunks)
            span.set_attribute("llm.response_length", len(full_response))
            span.set_attribute("llm.chunk_count", len(chunks))

            return {"message": message, "response": full_response, "chunks": len(chunks)}
        except Exception as e:
            span.set_attribute("error", str(e))
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
