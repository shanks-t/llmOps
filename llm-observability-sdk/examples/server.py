"""
Unified FastAPI Service with Google ADK Auto-Instrumentation

This service demonstrates 5 different LLM workflow patterns, all auto-instrumented
by the LLM Ops SDK. No manual decorators or enrichment calls needed - just call
llmops.init() and all ADK operations are automatically traced.

Endpoints:
    1. POST /chat      - Simple single-turn LLM conversation
    2. POST /travel    - Multi-tool travel agent (weather, hotels, flights, attractions)
    3. POST /code      - Code assistant (generate, explain, review code)
    4. POST /research  - Sequential multi-step workflow (search -> analyze -> summarize)
    5. GET  /stream    - Server-sent events streaming response

Prerequisites:
    1. Create llmops.yaml in project root (see examples/llmops.yaml)
    2. Set GOOGLE_API_KEY environment variable
    3. Start observability backend:
       - Phoenix: cd docker && docker-compose up phoenix -d
       - MLflow: cd docker && docker-compose up mlflow -d

Run:
    uv run uvicorn examples.server:app --reload

View traces:
    Phoenix: http://localhost:6006
    MLflow: http://localhost:5001
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Initialize LLM Ops SDK with auto-instrumentation BEFORE importing ADK
from pathlib import Path
import llmops

# Load config from the examples directory
config_path = Path(__file__).parent / "llmops.yaml"
llmops.init(config_path=config_path)

# Now import Google ADK components
from google import genai
from google.genai import types
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ChatRequest(BaseModel):
    """Simple chat request."""
    message: str


class ChatResponse(BaseModel):
    """Simple chat response."""
    message: str
    response: str


class TravelRequest(BaseModel):
    """Travel agent request."""
    query: str
    user_id: str = "default_user"


class TravelResponse(BaseModel):
    """Travel agent response."""
    query: str
    response: str
    tools_used: list[str]


class CodeRequest(BaseModel):
    """Code assistant request."""
    task: str  # "generate", "explain", or "review"
    prompt: str
    language: str = "python"


class CodeResponse(BaseModel):
    """Code assistant response."""
    task: str
    prompt: str
    response: str


class ResearchRequest(BaseModel):
    """Research workflow request."""
    topic: str
    depth: str = "standard"  # "quick", "standard", or "deep"


class ResearchResponse(BaseModel):
    """Research workflow response."""
    topic: str
    summary: str
    sources: list[str]
    key_findings: list[str]


# =============================================================================
# TOOL FUNCTIONS - Auto-instrumented by ADK + LLM Ops SDK
# =============================================================================


def get_weather(city: str) -> dict:
    """Get current weather for a city.

    Args:
        city: The name of the city to get weather for.

    Returns:
        Weather information including temperature, condition, and humidity.
    """
    weather_db = {
        "paris": {"temp_c": 18, "temp_f": 64, "condition": "Partly Cloudy", "humidity": 65, "wind_kph": 12},
        "london": {"temp_c": 14, "temp_f": 57, "condition": "Rainy", "humidity": 80, "wind_kph": 20},
        "tokyo": {"temp_c": 26, "temp_f": 79, "condition": "Sunny", "humidity": 70, "wind_kph": 8},
        "new york": {"temp_c": 22, "temp_f": 72, "condition": "Clear", "humidity": 55, "wind_kph": 15},
        "sydney": {"temp_c": 20, "temp_f": 68, "condition": "Sunny", "humidity": 60, "wind_kph": 18},
        "dubai": {"temp_c": 38, "temp_f": 100, "condition": "Hot", "humidity": 40, "wind_kph": 10},
    }
    result = weather_db.get(city.lower(), {
        "temp_c": 20, "temp_f": 68, "condition": "Unknown", "humidity": 50, "wind_kph": 10
    })
    return {"city": city, **result}


def get_local_time(city: str) -> dict:
    """Get current local time in a city.

    Args:
        city: The name of the city to get local time for.

    Returns:
        Local time information including time, date, and timezone.
    """
    offsets = {
        "paris": 1, "london": 0, "tokyo": 9, "new york": -5,
        "sydney": 11, "dubai": 4, "los angeles": -8, "singapore": 8
    }
    offset = offsets.get(city.lower(), 0)
    local_time = datetime.now(timezone(timedelta(hours=offset)))
    return {
        "city": city,
        "time": local_time.strftime("%H:%M"),
        "date": local_time.strftime("%Y-%m-%d"),
        "day_of_week": local_time.strftime("%A"),
        "timezone": f"UTC{'+' if offset >= 0 else ''}{offset}"
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

    city_data = attractions_db.get(city.lower(), {
        "all": [{"name": "Local Landmark", "rating": 4.0, "type": "General"}]
    })

    if category == "all":
        all_attractions = []
        for cat_attractions in city_data.values():
            all_attractions.extend(cat_attractions)
        return {"city": city, "category": category, "attractions": all_attractions}

    return {
        "city": city,
        "category": category,
        "attractions": city_data.get(category, [])
    }


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

    base = base_prices.get(
        (origin.lower(), destination.lower()),
        random.randint(300, 900)
    )

    multipliers = {"economy": 1.0, "business": 2.8, "first": 5.5}
    multiplier = multipliers.get(travel_class, 1.0)

    return {
        "origin": origin,
        "destination": destination,
        "class": travel_class,
        "options": [
            {"airline": "SkyWings", "price": int(base * multiplier), "duration": "12h 30m", "stops": 0},
            {"airline": "GlobalAir", "price": int(base * multiplier * 0.9), "duration": "14h 45m", "stops": 1},
            {"airline": "AeroConnect", "price": int(base * multiplier * 0.8), "duration": "16h 20m", "stops": 2},
        ]
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
                {"name": "Hotel Ibis", "price_per_night": 85, "rating": 3.8, "amenities": ["wifi", "breakfast"]},
                {"name": "Generator Paris", "price_per_night": 65, "rating": 4.0, "amenities": ["wifi", "bar"]},
            ],
            "mid-range": [
                {"name": "Novotel Paris", "price_per_night": 180, "rating": 4.2, "amenities": ["wifi", "gym", "restaurant"]},
                {"name": "Hotel Le Marais", "price_per_night": 200, "rating": 4.4, "amenities": ["wifi", "breakfast", "spa"]},
            ],
            "luxury": [
                {"name": "Ritz Paris", "price_per_night": 950, "rating": 4.9, "amenities": ["wifi", "pool", "spa", "gym", "restaurant"]},
                {"name": "Four Seasons George V", "price_per_night": 1200, "rating": 4.9, "amenities": ["wifi", "pool", "spa", "gym", "restaurant", "concierge"]},
            ],
        },
        "tokyo": {
            "budget": [
                {"name": "APA Hotel", "price_per_night": 70, "rating": 3.9, "amenities": ["wifi"]},
                {"name": "Toyoko Inn", "price_per_night": 60, "rating": 3.7, "amenities": ["wifi", "breakfast"]},
            ],
            "mid-range": [
                {"name": "Hotel Gracery Shinjuku", "price_per_night": 150, "rating": 4.3, "amenities": ["wifi", "restaurant"]},
                {"name": "Mitsui Garden", "price_per_night": 175, "rating": 4.4, "amenities": ["wifi", "spa", "restaurant"]},
            ],
            "luxury": [
                {"name": "Park Hyatt Tokyo", "price_per_night": 650, "rating": 4.8, "amenities": ["wifi", "pool", "spa", "gym", "restaurant"]},
                {"name": "Aman Tokyo", "price_per_night": 1100, "rating": 4.9, "amenities": ["wifi", "pool", "spa", "gym", "restaurant", "onsen"]},
            ],
        },
    }

    city_hotels = hotels_db.get(city.lower(), {
        "mid-range": [{"name": "City Hotel", "price_per_night": 120, "rating": 4.0, "amenities": ["wifi"]}]
    })

    hotels = city_hotels.get(budget, city_hotels.get("mid-range", []))

    # Filter by amenities if specified
    if amenities:
        hotels = [h for h in hotels if all(a in h["amenities"] for a in amenities)]

    return {"city": city, "budget": budget, "hotels": hotels}


def search_knowledge_base(query: str, max_results: int = 5) -> dict:
    """Search the knowledge base for relevant information.

    Args:
        query: The search query.
        max_results: Maximum number of results to return.

    Returns:
        Search results with relevance scores and snippets.
    """
    # Simulated knowledge base search (in reality, this would query a vector DB)
    knowledge_base = {
        "quantum computing": [
            {"title": "Quantum Computing Fundamentals", "snippet": "Quantum computers use qubits instead of classical bits...", "relevance": 0.95},
            {"title": "Applications in Healthcare", "snippet": "Drug discovery and molecular simulation benefit from quantum...", "relevance": 0.88},
            {"title": "Current Limitations", "snippet": "Decoherence and error correction remain major challenges...", "relevance": 0.82},
        ],
        "machine learning": [
            {"title": "Deep Learning Overview", "snippet": "Neural networks with multiple layers enable complex pattern recognition...", "relevance": 0.94},
            {"title": "ML in Production", "snippet": "Deploying ML models requires careful consideration of latency and scale...", "relevance": 0.87},
        ],
        "climate change": [
            {"title": "Global Temperature Trends", "snippet": "Average global temperatures have risen 1.1°C since pre-industrial times...", "relevance": 0.96},
            {"title": "Renewable Energy Solutions", "snippet": "Solar and wind power are now cost-competitive with fossil fuels...", "relevance": 0.89},
        ],
    }

    # Find best matching topic
    query_lower = query.lower()
    results = []
    for topic, docs in knowledge_base.items():
        if topic in query_lower or any(word in query_lower for word in topic.split()):
            results.extend(docs)

    if not results:
        results = [{"title": "General Information", "snippet": f"Information about: {query}", "relevance": 0.5}]

    return {
        "query": query,
        "results": results[:max_results],
        "total_found": len(results)
    }


def analyze_text(text: str, analysis_type: str = "summary") -> dict:
    """Analyze text content.

    Args:
        text: The text to analyze.
        analysis_type: Type of analysis - "summary", "sentiment", "key_points", or "entities".

    Returns:
        Analysis results based on the specified type.
    """
    # Simulated text analysis (in reality, this could use NLP models)
    word_count = len(text.split())

    if analysis_type == "summary":
        return {
            "type": "summary",
            "word_count": word_count,
            "summary": text[:200] + "..." if len(text) > 200 else text
        }
    elif analysis_type == "sentiment":
        # Simple heuristic-based sentiment
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
        # Extract sentences as key points
        sentences = text.split(". ")[:3]
        return {"type": "key_points", "points": sentences}
    else:
        return {"type": analysis_type, "result": "Analysis not available"}


# =============================================================================
# ADK AGENTS
# =============================================================================


# Agent 1: Simple conversational agent (for /chat endpoint)
chat_agent = Agent(
    name="chat_assistant",
    model="gemini-2.0-flash-exp",
    description="A helpful conversational assistant for general questions.",
    instruction="""You are a helpful, friendly assistant. Answer questions clearly and concisely.
    Be informative but not overly verbose. If you don't know something, say so honestly.""",
    tools=[],  # No tools - pure LLM conversation
)

# Agent 2: Travel agent with multiple tools (for /travel endpoint)
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

# Agent 3: Code assistant (for /code endpoint)
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
    tools=[],  # Pure LLM for code tasks
)

# Agent 4: Research agent with retrieval tools (for /research endpoint)
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


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================


session_service = InMemorySessionService()


def create_runner(agent: Agent) -> Runner:
    """Create a runner for an agent."""
    return Runner(
        agent=agent,
        app_name="llmops_demo",
        session_service=session_service,
    )


async def run_agent(agent: Agent, query: str, user_id: str = "default") -> tuple[str, list[str]]:
    """Run an agent and collect the response.

    Returns:
        Tuple of (response_text, tools_used)
    """
    runner = create_runner(agent)

    session = await session_service.create_session(
        app_name="llmops_demo",
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
        # Collect response text
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

        # Track tool usage
        if hasattr(event, "tool_calls") and event.tool_calls:
            for tool_call in event.tool_calls:
                if hasattr(tool_call, "name"):
                    tools_used.append(tool_call.name)

    return response_text, tools_used


async def stream_agent_response(agent: Agent, query: str, user_id: str = "default") -> AsyncIterator[str]:
    """Stream agent response as server-sent events."""
    runner = create_runner(agent)

    session = await session_service.create_session(
        app_name="llmops_demo",
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
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    # Format as SSE
                    yield f"data: {part.text}\n\n"

    yield "data: [DONE]\n\n"


# =============================================================================
# FASTAPI APP
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting LLM Ops Demo Service...")
    print(f"Backend: {llmops.get_backend()}")

    yield

    # Shutdown
    print("Shutting down...")
    llmops.shutdown()


app = FastAPI(
    title="LLM Ops Demo Service",
    description="Demonstrates various LLM workflow patterns with auto-instrumentation",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Service information and available endpoints."""
    return {
        "service": "LLM Ops Demo",
        "version": "1.0.0",
        "backend": llmops.get_backend(),
        "configured": llmops.is_configured(),
        "endpoints": {
            "POST /chat": "Simple single-turn LLM conversation",
            "POST /travel": "Multi-tool travel agent",
            "POST /code": "Code generation, explanation, and review",
            "POST /research": "Sequential research workflow with retrieval",
            "GET /stream": "Streaming response via SSE",
        },
        "examples": {
            "chat": 'curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d \'{"message": "What is photosynthesis?"}\'',
            "travel": 'curl -X POST http://localhost:8000/travel -H "Content-Type: application/json" -d \'{"query": "Plan a trip to Tokyo"}\'',
            "code": 'curl -X POST http://localhost:8000/code -H "Content-Type: application/json" -d \'{"task": "generate", "prompt": "fibonacci function"}\'',
            "research": 'curl -X POST http://localhost:8000/research -H "Content-Type: application/json" -d \'{"topic": "quantum computing"}\'',
            "stream": "curl -N 'http://localhost:8000/stream?prompt=Explain%20gravity'",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "backend": llmops.get_backend(),
        "google_api_key": "configured" if os.getenv("GOOGLE_API_KEY") else "missing",
    }


# -----------------------------------------------------------------------------
# Endpoint 1: Simple Chat
# -----------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Simple single-turn LLM conversation.

    This endpoint demonstrates the most basic LLM interaction pattern:
    - Single user message in
    - Single assistant response out
    - No tools, no memory, no complex workflows

    Auto-instrumentation captures:
    - LLM call with model, tokens, latency
    - Input/output content (if capture enabled)
    """
    response, _ = await run_agent(chat_agent, request.message)

    return ChatResponse(
        message=request.message,
        response=response,
    )


# -----------------------------------------------------------------------------
# Endpoint 2: Multi-Tool Travel Agent
# -----------------------------------------------------------------------------


@app.post("/travel", response_model=TravelResponse)
async def travel(request: TravelRequest):
    """Multi-tool travel planning agent.

    This endpoint demonstrates a sophisticated agent that:
    - Understands complex travel queries
    - Uses multiple tools autonomously (weather, hotels, flights, attractions)
    - Synthesizes information into helpful responses

    Auto-instrumentation captures:
    - Agent invocation span (parent)
    - Individual tool call spans (children)
    - LLM calls for reasoning
    - Complete trace hierarchy
    """
    response, tools_used = await run_agent(
        travel_agent,
        request.query,
        user_id=request.user_id,
    )

    return TravelResponse(
        query=request.query,
        response=response,
        tools_used=list(set(tools_used)),  # Deduplicate
    )


# -----------------------------------------------------------------------------
# Endpoint 3: Code Assistant
# -----------------------------------------------------------------------------


@app.post("/code", response_model=CodeResponse)
async def code(request: CodeRequest):
    """Code generation, explanation, and review.

    This endpoint demonstrates specialized LLM usage:
    - Task-specific prompting (generate/explain/review)
    - Language-aware responses
    - Technical domain expertise

    Auto-instrumentation captures:
    - LLM call with full prompt context
    - Token usage for potentially long code outputs
    """
    task_prompts = {
        "generate": f"Generate {request.language} code for: {request.prompt}",
        "explain": f"Explain this {request.language} code: {request.prompt}",
        "review": f"Review this {request.language} code for bugs and improvements: {request.prompt}",
    }

    prompt = task_prompts.get(request.task, request.prompt)
    response, _ = await run_agent(code_agent, prompt)

    return CodeResponse(
        task=request.task,
        prompt=request.prompt,
        response=response,
    )


# -----------------------------------------------------------------------------
# Endpoint 4: Research Workflow
# -----------------------------------------------------------------------------


@app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    """Sequential multi-step research workflow.

    This endpoint demonstrates a retrieval-augmented generation (RAG) pattern:
    1. Search knowledge base for relevant information
    2. Analyze retrieved content
    3. Synthesize into structured findings

    Auto-instrumentation captures:
    - Full workflow as parent span
    - Individual tool calls (search, analyze)
    - LLM reasoning between steps
    """
    depth_instructions = {
        "quick": "Provide a brief overview with 2-3 key points.",
        "standard": "Provide a comprehensive summary with key findings and sources.",
        "deep": "Provide an exhaustive analysis covering all aspects, nuances, and implications.",
    }

    prompt = f"""Research the following topic: {request.topic}

    Depth level: {request.depth}
    Instructions: {depth_instructions.get(request.depth, depth_instructions['standard'])}

    Use the search_knowledge_base tool to find information, then analyze and synthesize your findings.
    Structure your response with: Summary, Key Findings (as bullet points), and Sources."""

    response, tools_used = await run_agent(research_agent, prompt)

    # Parse response for structured output (simplified)
    sources = ["search_knowledge_base"] if "search_knowledge_base" in tools_used else []
    key_findings = [line.strip() for line in response.split("\n") if line.strip().startswith("-")][:5]

    return ResearchResponse(
        topic=request.topic,
        summary=response,
        sources=sources,
        key_findings=key_findings if key_findings else ["See summary for details"],
    )


# -----------------------------------------------------------------------------
# Endpoint 5: Streaming Response
# -----------------------------------------------------------------------------


@app.get("/stream")
async def stream(prompt: str = Query(..., description="The prompt for streaming response")):
    """Streaming response via Server-Sent Events.

    This endpoint demonstrates real-time streaming:
    - Tokens streamed as they're generated
    - Server-Sent Events (SSE) format
    - Low latency for first token

    Auto-instrumentation captures:
    - Stream start/end times
    - Time to first token
    - Total tokens streamed
    """
    return StreamingResponse(
        stream_agent_response(chat_agent, prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
