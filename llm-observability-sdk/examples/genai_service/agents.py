"""
agents.py

Agent definitions, tools, and runner utilities for the GenAI service.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any

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
    weather_db = {
        "paris": {
            "temp_c": 18,
            "temp_f": 64,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind_kph": 12,
        },
        "london": {
            "temp_c": 14,
            "temp_f": 57,
            "condition": "Rainy",
            "humidity": 80,
            "wind_kph": 20,
        },
        "tokyo": {"temp_c": 26, "temp_f": 79, "condition": "Sunny", "humidity": 70, "wind_kph": 8},
        "new york": {
            "temp_c": 22,
            "temp_f": 72,
            "condition": "Clear",
            "humidity": 55,
            "wind_kph": 15,
        },
        "sydney": {
            "temp_c": 20,
            "temp_f": 68,
            "condition": "Sunny",
            "humidity": 60,
            "wind_kph": 18,
        },
        "dubai": {"temp_c": 38, "temp_f": 100, "condition": "Hot", "humidity": 40, "wind_kph": 10},
    }
    result = weather_db.get(
        city.lower(),
        {"temp_c": 20, "temp_f": 68, "condition": "Unknown", "humidity": 50, "wind_kph": 10},
    )
    return {"city": city, **result}


def get_local_time(city: str) -> dict:
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
        "dubai": 4,
        "los angeles": -8,
        "singapore": 8,
    }
    offset = offsets.get(city.lower(), 0)
    local_time = datetime.now(timezone(timedelta(hours=offset)))
    return {
        "city": city,
        "time": local_time.strftime("%H:%M"),
        "date": local_time.strftime("%Y-%m-%d"),
        "day_of_week": local_time.strftime("%A"),
        "timezone": f"UTC{'+' if offset >= 0 else ''}{offset}",
    }


def get_attractions(city: str, category: str = "all") -> dict:
    """Get tourist attractions in a city.

    Args:
        city: The name of the city to get attractions for.
        category: Category filter - "all", "cultural", "outdoor", or "entertainment".

    Returns:
        List of attractions with ratings and descriptions.
    """
    attractions_db = {
        "paris": {
            "cultural": [
                {"name": "Louvre Museum", "rating": 4.8, "type": "Museum"},
                {"name": "Notre-Dame Cathedral", "rating": 4.7, "type": "Historical"},
            ],
            "outdoor": [
                {"name": "Eiffel Tower", "rating": 4.9, "type": "Landmark"},
                {"name": "Luxembourg Gardens", "rating": 4.6, "type": "Park"},
            ],
            "entertainment": [
                {"name": "Moulin Rouge", "rating": 4.5, "type": "Show"},
                {"name": "Champs-Élysées", "rating": 4.4, "type": "Shopping"},
            ],
        },
        "tokyo": {
            "cultural": [
                {"name": "Senso-ji Temple", "rating": 4.7, "type": "Temple"},
                {"name": "Tokyo National Museum", "rating": 4.6, "type": "Museum"},
            ],
            "outdoor": [
                {"name": "Shibuya Crossing", "rating": 4.5, "type": "Landmark"},
                {"name": "Ueno Park", "rating": 4.4, "type": "Park"},
            ],
            "entertainment": [
                {"name": "teamLab Borderless", "rating": 4.8, "type": "Art"},
                {"name": "Akihabara", "rating": 4.5, "type": "Shopping"},
            ],
        },
    }

    city_data = attractions_db.get(
        city.lower(), {"all": [{"name": "Local Landmark", "rating": 4.0, "type": "General"}]}
    )

    if category == "all":
        all_attractions = []
        for cat_attractions in city_data.values():
            all_attractions.extend(cat_attractions)
        return {"city": city, "category": category, "attractions": all_attractions}

    return {"city": city, "category": category, "attractions": city_data.get(category, [])}


def get_flight_prices(origin: str, destination: str, travel_class: str = "economy") -> dict:
    """Get flight prices between two cities.

    Args:
        origin: Departure city.
        destination: Arrival city.
        travel_class: Class of travel - "economy", "business", or "first".

    Returns:
        Flight options with prices and durations.
    """
    import random

    base_prices = {
        ("new york", "paris"): 450,
        ("new york", "tokyo"): 850,
        ("london", "tokyo"): 750,
        ("sydney", "tokyo"): 550,
    }

    base = base_prices.get((origin.lower(), destination.lower()), random.randint(300, 900))

    multipliers = {"economy": 1.0, "business": 2.8, "first": 5.5}
    multiplier = multipliers.get(travel_class, 1.0)

    return {
        "origin": origin,
        "destination": destination,
        "class": travel_class,
        "options": [
            {
                "airline": "SkyWings",
                "price": int(base * multiplier),
                "duration": "12h 30m",
                "stops": 0,
            },
            {
                "airline": "GlobalAir",
                "price": int(base * multiplier * 0.9),
                "duration": "14h 45m",
                "stops": 1,
            },
            {
                "airline": "AeroConnect",
                "price": int(base * multiplier * 0.8),
                "duration": "16h 20m",
                "stops": 2,
            },
        ],
    }


def get_hotels(city: str, budget: str = "mid-range", amenities: list[str] | None = None) -> dict:
    """Get hotel recommendations in a city.

    Args:
        city: The name of the city.
        budget: Budget level - "budget", "mid-range", or "luxury".
        amenities: Optional list of required amenities like "wifi", "pool", "gym".

    Returns:
        Hotel recommendations with prices and ratings.
    """
    hotels_db = {
        "paris": {
            "budget": [
                {
                    "name": "Hotel Ibis",
                    "price_per_night": 85,
                    "rating": 3.8,
                    "amenities": ["wifi", "breakfast"],
                },
                {
                    "name": "Generator Paris",
                    "price_per_night": 65,
                    "rating": 4.0,
                    "amenities": ["wifi", "bar"],
                },
            ],
            "mid-range": [
                {
                    "name": "Novotel Paris",
                    "price_per_night": 180,
                    "rating": 4.2,
                    "amenities": ["wifi", "gym", "restaurant"],
                },
                {
                    "name": "Hotel Le Marais",
                    "price_per_night": 200,
                    "rating": 4.4,
                    "amenities": ["wifi", "breakfast", "spa"],
                },
            ],
            "luxury": [
                {
                    "name": "Ritz Paris",
                    "price_per_night": 950,
                    "rating": 4.9,
                    "amenities": ["wifi", "pool", "spa", "gym", "restaurant"],
                },
                {
                    "name": "Four Seasons George V",
                    "price_per_night": 1200,
                    "rating": 4.9,
                    "amenities": ["wifi", "pool", "spa", "gym", "restaurant", "concierge"],
                },
            ],
        },
        "tokyo": {
            "budget": [
                {"name": "APA Hotel", "price_per_night": 70, "rating": 3.9, "amenities": ["wifi"]},
                {
                    "name": "Toyoko Inn",
                    "price_per_night": 60,
                    "rating": 3.7,
                    "amenities": ["wifi", "breakfast"],
                },
            ],
            "mid-range": [
                {
                    "name": "Hotel Gracery Shinjuku",
                    "price_per_night": 150,
                    "rating": 4.3,
                    "amenities": ["wifi", "restaurant"],
                },
                {
                    "name": "Mitsui Garden",
                    "price_per_night": 175,
                    "rating": 4.4,
                    "amenities": ["wifi", "spa", "restaurant"],
                },
            ],
            "luxury": [
                {
                    "name": "Park Hyatt Tokyo",
                    "price_per_night": 650,
                    "rating": 4.8,
                    "amenities": ["wifi", "pool", "spa", "gym", "restaurant"],
                },
                {
                    "name": "Aman Tokyo",
                    "price_per_night": 1100,
                    "rating": 4.9,
                    "amenities": ["wifi", "pool", "spa", "gym", "restaurant", "onsen"],
                },
            ],
        },
    }

    city_hotels = hotels_db.get(
        city.lower(),
        {
            "mid-range": [
                {"name": "City Hotel", "price_per_night": 120, "rating": 4.0, "amenities": ["wifi"]}
            ]
        },
    )

    hotels = city_hotels.get(budget, city_hotels.get("mid-range", []))

    if amenities:
        hotels = [h for h in hotels if all(a in h["amenities"] for a in amenities)]  # type: ignore[operator]

    return {"city": city, "budget": budget, "hotels": hotels}


def search_knowledge_base(query: str, max_results: int = 5) -> dict:
    """Search the knowledge base for relevant information.

    Args:
        query: The search query.
        max_results: Maximum number of results to return.

    Returns:
        Search results with relevance scores and snippets.
    """
    knowledge_base = {
        "quantum computing": [
            {
                "title": "Quantum Computing Fundamentals",
                "snippet": "Quantum computers use qubits instead of classical bits...",
                "relevance": 0.95,
            },
            {
                "title": "Applications in Healthcare",
                "snippet": "Drug discovery and molecular simulation benefit from quantum...",
                "relevance": 0.88,
            },
            {
                "title": "Current Limitations",
                "snippet": "Decoherence and error correction remain major challenges...",
                "relevance": 0.82,
            },
        ],
        "machine learning": [
            {
                "title": "Deep Learning Overview",
                "snippet": "Neural networks with multiple layers enable complex pattern recognition...",
                "relevance": 0.94,
            },
            {
                "title": "ML in Production",
                "snippet": "Deploying ML models requires careful consideration of latency and scale...",
                "relevance": 0.87,
            },
        ],
        "climate change": [
            {
                "title": "Global Temperature Trends",
                "snippet": "Average global temperatures have risen 1.1°C since pre-industrial times...",
                "relevance": 0.96,
            },
            {
                "title": "Renewable Energy Solutions",
                "snippet": "Solar and wind power are now cost-competitive with fossil fuels...",
                "relevance": 0.89,
            },
        ],
    }

    query_lower = query.lower()
    results = []
    for topic, docs in knowledge_base.items():
        if topic in query_lower or any(word in query_lower for word in topic.split()):
            results.extend(docs)

    if not results:
        results = [
            {
                "title": "General Information",
                "snippet": f"Information about: {query}",
                "relevance": 0.5,
            }
        ]

    return {"query": query, "results": results[:max_results], "total_found": len(results)}


def analyze_text(text: str, analysis_type: str = "summary") -> dict:
    """Analyze text content.

    Args:
        text: The text to analyze.
        analysis_type: Type of analysis - "summary", "sentiment", "key_points", or "entities".

    Returns:
        Analysis results based on the specified type.
    """
    word_count = len(text.split())

    if analysis_type == "summary":
        return {
            "type": "summary",
            "word_count": word_count,
            "summary": text[:200] + "..." if len(text) > 200 else text,
        }
    elif analysis_type == "sentiment":
        positive_words = ["good", "great", "excellent", "amazing", "beneficial", "promising"]
        negative_words = ["bad", "poor", "terrible", "harmful", "dangerous", "concerning"]
        text_lower = text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        if pos_count > neg_count:
            sentiment = "positive"
        elif neg_count > pos_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        return {"type": "sentiment", "sentiment": sentiment, "confidence": 0.75}
    elif analysis_type == "key_points":
        sentences = text.split(". ")[:3]
        return {"type": "key_points", "points": sentences}
    else:
        return {"type": analysis_type, "result": "Analysis not available"}


# =============================================================================
# GCS TOOLS FOR MEDICAL RECORDS
# =============================================================================


def _run_gcloud(args: list[str]) -> str:
    """Run a gcloud command and return output.

    Args:
        args: Command arguments (without 'gcloud').

    Returns:
        Command stdout.

    Raises:
        RuntimeError: If command fails.
    """
    import subprocess

    from config import get_config

    config = get_config()
    cmd = ["gcloud"] + args + [f"--project={config.project_id}"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gcloud command failed: {result.stderr}")
    return result.stdout


def list_patients() -> list[dict[str, Any]]:
    """List all patients from the index.

    Returns:
        List of patient metadata dicts.
    """
    import json

    from config import get_config

    config = get_config()
    output = _run_gcloud(["storage", "cat", config.index_uri])
    result: list[dict[str, Any]] = json.loads(output)
    return result


def fetch_patient_record(patient_id: str) -> dict[str, Any]:
    """Fetch a patient's FHIR record from GCS.

    Args:
        patient_id: The patient ID (e.g., "patient-001").

    Returns:
        The FHIR bundle as a dict.
    """
    import json

    from config import get_config

    config = get_config()
    uri = f"{config.raw_uri}/{patient_id}.json"
    output = _run_gcloud(["storage", "cat", uri])
    result: dict[str, Any] = json.loads(output)
    return result


def save_summary(patient_id: str, summary: str, citations: list[dict]) -> dict:
    """Save a patient summary to GCS.

    Args:
        patient_id: The patient ID (e.g., "patient-001").
        summary: The summary text.
        citations: List of citation objects with section, resource_type, resource_id, excerpt.

    Returns:
        Confirmation with GCS path.
    """
    import json
    import tempfile

    from config import get_config

    config = get_config()
    summary_data = {
        "patient_id": patient_id,
        "summary": summary,
        "citations": citations,
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(summary_data, f, indent=2)
        temp_path = f.name

    try:
        dest_uri = f"{config.summaries_uri}/{patient_id}.json"
        _run_gcloud(["storage", "cp", temp_path, dest_uri])
        return {"status": "saved", "location": dest_uri}
    finally:
        import os

        os.unlink(temp_path)


# =============================================================================
# AGENT DEFINITIONS
# =============================================================================


chat_agent = Agent(
    name="chat_assistant",
    model="gemini-2.0-flash-exp",
    description="A helpful conversational assistant for general questions.",
    instruction="""You are a helpful, friendly assistant. Answer questions clearly and concisely.
    Be informative but not overly verbose. If you don't know something, say so honestly.""",
    tools=[],
)

travel_agent = Agent(
    name="travel_assistant",
    model="gemini-2.0-flash-exp",
    description="A comprehensive travel planning assistant.",
    instruction="""You are an expert travel assistant. Help users plan trips by:
    1. Gathering information about weather, attractions, hotels, and flights
    2. Making personalized recommendations based on user preferences
    3. Providing practical tips and local insights
    4. Creating cohesive travel itineraries when requested

    Always use the available tools to get accurate, current information.
    Be enthusiastic about travel while remaining helpful and practical.""",
    tools=[get_weather, get_local_time, get_attractions, get_flight_prices, get_hotels],
)

code_agent = Agent(
    name="code_assistant",
    model="gemini-2.0-flash-exp",
    description="A coding assistant that helps with code generation, explanation, and review.",
    instruction="""You are an expert software developer assistant. Your capabilities include:

    1. Code Generation: Write clean, efficient, well-documented code
    2. Code Explanation: Explain code logic, patterns, and best practices
    3. Code Review: Identify bugs, suggest improvements, highlight security issues

    When generating code:
    - Include helpful comments
    - Follow language-specific conventions
    - Handle edge cases appropriately
    - Provide usage examples

    When explaining code:
    - Break down complex logic step by step
    - Explain the 'why' not just the 'what'
    - Reference relevant design patterns

    When reviewing code:
    - Be constructive and specific
    - Prioritize issues by severity
    - Suggest concrete improvements""",
    tools=[],
)

research_agent = Agent(
    name="research_assistant",
    model="gemini-2.0-flash-exp",
    description="A research assistant that searches, analyzes, and synthesizes information.",
    instruction="""You are a thorough research assistant. For each research topic:

    1. SEARCH: Use the knowledge base tool to find relevant information
    2. ANALYZE: Examine the results for key insights and patterns
    3. SYNTHESIZE: Combine findings into a coherent summary

    Structure your research findings as:
    - Executive Summary (2-3 sentences)
    - Key Findings (bullet points)
    - Sources Consulted
    - Areas for Further Research (if applicable)

    Be objective and cite your sources. Distinguish between facts and interpretations.""",
    tools=[search_knowledge_base, analyze_text],
)

medical_records_agent = Agent(
    name="medical_records_assistant",
    model="gemini-2.0-flash-exp",
    description="A medical records summarization agent that creates clinical summaries with citations.",
    instruction="""You are a clinical documentation specialist. Your task is to summarize patient
medical records from FHIR bundles and provide citations for every clinical assertion.

WORKFLOW:
1. Use list_patients() to see available patients if needed
2. Use fetch_patient_record(patient_id) to retrieve the FHIR bundle
3. Analyze the bundle and create a structured summary
4. Use save_summary(patient_id, summary, citations) to save your work

REQUIRED SECTIONS in your summary:
- Demographics: Patient name, age, gender, address
- Active Conditions: Current diagnoses with onset dates
- Procedures/Surgical History: Past procedures with dates
- Current Medications: Active medication requests
- Recent Lab Results: Flag any abnormal values with reference ranges
- Imaging Findings: Diagnostic reports and imaging results

CITATION REQUIREMENTS:
Every clinical claim MUST include a citation object with:
- section: Which summary section this supports
- resource_type: FHIR resource type (Condition, Procedure, Observation, etc.)
- resource_id: The resource ID from the bundle
- excerpt: A brief excerpt from the source data

OUTPUT FORMAT:
Return ONLY a JSON object with this structure (no markdown, no code blocks, no additional text):
{
    "summary": "The clinical summary text with all required sections...",
    "citations": [
        {
            "section": "Active Conditions",
            "resource_type": "Condition",
            "resource_id": "abc123",
            "excerpt": "Essential hypertension (disorder), onset 2023-05-15"
        }
    ]
}

Be thorough but concise. Focus on clinically relevant information.""",
    tools=[list_patients, fetch_patient_record, save_summary],
)


# =============================================================================
# SESSION & RUNNER
# =============================================================================


session_service = InMemorySessionService()


def create_runner(agent: Agent) -> Runner:
    """Create a runner for an agent."""
    return Runner(
        agent=agent,
        app_name="genai_service",
        session_service=session_service,
    )


async def run_agent(agent: Agent, query: str, user_id: str = "default") -> tuple[str, list[str]]:
    """Run an agent and collect the response.

    Returns:
        Tuple of (response_text, tools_used)
    """
    runner = create_runner(agent)

    session = await session_service.create_session(
        app_name="genai_service",
        user_id=user_id,
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    response_text = ""
    tools_used = []

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

        if hasattr(event, "tool_calls") and event.tool_calls:
            for tool_call in event.tool_calls:
                if hasattr(tool_call, "name"):
                    tools_used.append(tool_call.name)

    return response_text, tools_used


async def stream_agent_response(
    agent: Agent, query: str, user_id: str = "default"
) -> AsyncIterator[str]:
    """Stream agent response as server-sent events."""
    runner = create_runner(agent)

    session = await session_service.create_session(
        app_name="genai_service",
        user_id=user_id,
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        if hasattr(event, "content") and event.content:
            if event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        yield f"data: {part.text}\n\n"

    yield "data: [DONE]\n\n"
